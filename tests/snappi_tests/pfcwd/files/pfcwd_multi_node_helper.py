import time
from math import ceil
import logging

from tests.common.helpers.assertions import pytest_assert, pytest_require
from tests.common.fixtures.conn_graph_facts import conn_graph_facts, fanout_graph_facts     # noqa: F401
from tests.common.snappi_tests.snappi_helpers import get_dut_port_id                              # noqa: F401
from tests.common.snappi_tests.common_helpers import pfc_class_enable_vector, \
    start_pfcwd, enable_packet_aging, get_pfcwd_poll_interval, get_pfcwd_detect_time, \
    sec_to_nanosec                                                                                # noqa: F401
from tests.common.snappi_tests.port import select_ports                                           # noqa: F401
from tests.common.snappi_tests.snappi_helpers import wait_for_arp                                 # noqa: F401
from tests.common.snappi_tests.snappi_test_params import SnappiTestParams
from tests.common.snappi_tests.variables import pfcQueueGroupSize, pfcQueueValueDict
from tests.common.snappi_tests.snappi_fixtures import gen_data_flow_dest_ip

logger = logging.getLogger(__name__)

PAUSE_FLOW_NAME = 'Pause Storm'
WARM_UP_TRAFFIC_NAME = "Warm Up Traffic"
TEST_FLOW_NAME = 'Test Flow'
BG_FLOW_NAME = 'Background Flow'
WARM_UP_TRAFFIC_DUR = 1
DATA_PKT_SIZE = 1024
SNAPPI_POLL_DELAY_SEC = 2
TOLERANCE_THRESHOLD = 0.05
UDP_SRC_START = 5000


def run_pfcwd_multi_node_test(api,
                              testbed_config,
                              port_config_list,
                              conn_data,
                              fanout_data,
                              dut_port,
                              pause_prio_list,
                              test_prio_list,
                              bg_prio_list,
                              prio_dscp_map,
                              trigger_pfcwd,
                              pattern,
                              snappi_extra_params=None):
    """
    Run multidut PFC watchdog test in a multi-node (>=3) topoology

    Args:
        api (obj): SNAPPI session
        testbed_config (obj): testbed L1/L2/L3 configuration
        port_config_list (list): list of port configuration
        conn_data (dict): the dictionary returned by conn_graph_fact.
        fanout_data (dict): the dictionary returned by fanout_graph_fact.
        dut_port (str): DUT port to test
        pause_prio_list (list): priorities to pause for PFC pause storm
        test_prio_list (list): priorities of test flows
        bg_prio_list (list): priorities of background flows
        prio_dscp_map (dict): Priority vs. DSCP map (key = priority).
        trigger_pfcwd (bool): if PFC watchdog is expected to be triggered
        pattern (str): traffic pattern
        snappi_extra_params (SnappiTestParams obj): additional parameters for Snappi traffic
    Returns:
        N/A
    """
    patterns = ['all to all', 'many to one']
    if pattern not in patterns:
        raise ValueError('invalid traffic pattern passed in "{}", must be {}'.format(
            pattern, ' or '.join(['"{}"'.format(src) for src in patterns])))

    if snappi_extra_params is None:
        snappi_extra_params = SnappiTestParams()

    # Traffic flow:
    # tx_port (TGEN) --- ingress DUT --- egress DUT --- rx_port (TGEN)

    # initialize the (duthost, port) set.
    # The final list will have all the asics which needs to be configured for PFC
    pfcwd_to_be_configured = set()

    rx_port = snappi_extra_params.multi_dut_params.multi_dut_ports[0]
    egress_duthost = rx_port['duthost']
    # Add the port to the set of ports to be configured for PFC
    pfcwd_to_be_configured.add((egress_duthost, rx_port['asic_value']))

    tx_port = [snappi_extra_params.multi_dut_params.multi_dut_ports[1],
               snappi_extra_params.multi_dut_params.multi_dut_ports[2]]
    if pattern == 'all to all':
        tx_port_id_list = [rx_port["port_id"], tx_port[0]["port_id"], tx_port[1]["port_id"]]
        rx_port_id_list = [rx_port["port_id"], tx_port[0]["port_id"], tx_port[1]["port_id"]]
        pfcwd_to_be_configured.add((rx_port['duthost'], rx_port['asic_value']))
    elif pattern == 'many to one':
        tx_port_id_list = [tx_port[0]["port_id"], tx_port[1]["port_id"]]
        rx_port_id_list = [rx_port["port_id"]]
    # add ingress DUT into the set
    pfcwd_to_be_configured.add((tx_port[0]['duthost'], tx_port[0]['asic_value']))
    pfcwd_to_be_configured.add((tx_port[1]['duthost'], tx_port[1]['asic_value']))

    pytest_assert(testbed_config is not None, 'Fail to get L2/3 testbed config')
    num_ports = len(port_config_list)
    pytest_require(num_ports >= 3, "This test requires at least 3 ports")

    # Enable PFC watchdog on the rx side and tx side of the DUT without duplication.
    for duthost, asic in pfcwd_to_be_configured:
        start_pfcwd(duthost, asic)
        enable_packet_aging(duthost)

    poll_interval_sec = get_pfcwd_poll_interval(egress_duthost, rx_port['asic_value']) / 1000.0
    detect_time_sec = get_pfcwd_detect_time(host_ans=egress_duthost, intf=rx_port['peer_port'],
                                            asic_value=rx_port['asic_value']) / 1000.0

    if trigger_pfcwd:
        pfc_storm_dur_sec = poll_interval_sec + detect_time_sec
    else:
        pfc_storm_dur_sec = 0.5 * detect_time_sec

    exp_dur_sec = ceil(pfc_storm_dur_sec + 1)
    cisco_platform = "Cisco" in egress_duthost.facts['hwsku']

    speed_str = testbed_config.layer1[0].speed
    speed_gbps = int(speed_str.split('_')[1])
    TEST_FLOW_AGGR_RATE_PERCENT = 45
    BG_FLOW_AGGR_RATE_PERCENT = 45
    # Backplane is 200G in Cisco platforms.
    if speed_gbps > 200 and cisco_platform:
        TEST_FLOW_AGGR_RATE_PERCENT = TEST_FLOW_AGGR_RATE_PERCENT * 200 / speed_gbps
        BG_FLOW_AGGR_RATE_PERCENT = BG_FLOW_AGGR_RATE_PERCENT * 200 / speed_gbps

    """ Generate traffic config """
    test_flow_rate_percent = int(TEST_FLOW_AGGR_RATE_PERCENT /
                                 (num_ports - 1) /
                                 len(test_prio_list))

    bg_flow_rate_percent = int(BG_FLOW_AGGR_RATE_PERCENT /
                               (num_ports - 1) /
                               len(bg_prio_list))

    __gen_traffic(testbed_config=testbed_config,
                  port_config_list=port_config_list,
                  rx_port_id_list=rx_port_id_list,
                  tx_port_id_list=tx_port_id_list,
                  pause_flow_name=PAUSE_FLOW_NAME,
                  pause_prio_list=pause_prio_list,
                  test_flow_name=TEST_FLOW_NAME,
                  test_flow_prio_list=test_prio_list,
                  test_flow_rate_percent=test_flow_rate_percent,
                  bg_flow_name=BG_FLOW_NAME,
                  bg_flow_prio_list=bg_prio_list,
                  bg_flow_rate_percent=bg_flow_rate_percent,
                  data_flow_dur_sec=exp_dur_sec,
                  pfc_storm_dur_sec=pfc_storm_dur_sec,
                  data_pkt_size=DATA_PKT_SIZE,
                  prio_dscp_map=prio_dscp_map,
                  traffic_pattern=pattern)

    flows = testbed_config.flows

    all_flow_names = [flow.name for flow in flows]

    flow_stats = __run_traffic(api=api,
                               config=testbed_config,
                               all_flow_names=all_flow_names,
                               exp_dur_sec=exp_dur_sec)

    """ Retrieve ASIC information for DUT """
    asic_type = egress_duthost.facts['asic_type']

    rx_tx_tol_thrhlds = [0.0001, 0.0002]  # Maintain a 0.01% and 0.02% deviation between tx and rx frames

    __verify_results(rows=flow_stats,
                     speed_gbps=speed_gbps,
                     pause_flow_name=PAUSE_FLOW_NAME,
                     test_flow_name=TEST_FLOW_NAME,
                     bg_flow_name=BG_FLOW_NAME,
                     test_flow_rate_percent=test_flow_rate_percent,
                     bg_flow_rate_percent=bg_flow_rate_percent,
                     data_flow_dur_sec=exp_dur_sec,
                     data_pkt_size=DATA_PKT_SIZE,
                     trigger_pfcwd=trigger_pfcwd,
                     pause_port_id=rx_port_id_list[0],
                     rx_deviation=TOLERANCE_THRESHOLD,
                     rx_tx_deviations=rx_tx_tol_thrhlds,
                     asic_type=asic_type)


def __data_flow_name(name_prefix, src_id, dst_id, prio):
    """
    Generate name for a data flow

    Args:
        name_prefix (str): name prefix
        src_id (int): ID of the source port
        dst_id (int): ID of the destination port
        prio (int): priority of the flow

    Returns:
        Name of the flow (str)
    """
    return "{} {} -> {} Prio {}".format(name_prefix, src_id, dst_id, prio)


def __data_flow_src(flow_name):
    """
    Get the source ID from the data flow's name

    Args:
        flow_name (str): name of the data flow

    Returns:
        ID of the source port (str)
    """
    words = flow_name.split()
    index = words.index('->')
    return int(words[index - 1])


def __data_flow_dst(flow_name):
    """
    Get the destination ID from the data flow's name

    Args:
        flow_name (str): name of the data flow

    Returns:
        ID of the destination port (str)
    """
    words = flow_name.split()
    index = words.index('->')
    return int(words[index + 1])


def __gen_traffic(testbed_config,
                  port_config_list,
                  rx_port_id_list,
                  tx_port_id_list,
                  pause_flow_name,
                  pause_prio_list,
                  test_flow_name,
                  test_flow_prio_list,
                  test_flow_rate_percent,
                  bg_flow_name,
                  bg_flow_prio_list,
                  bg_flow_rate_percent,
                  data_flow_dur_sec,
                  pfc_storm_dur_sec,
                  data_pkt_size,
                  prio_dscp_map,
                  traffic_pattern):
    """
    Generate configurations of flows under all to all traffic pattern, including
    test flows, background flows and pause storm. Test flows and background flows
    are also known as data flows.

    Args:
        testbed_config (obj): testbed L1/L2/L3 configuration
        port_config_list (list): list of port configuration
        port_id (int): ID of DUT port to test.
        pause_flow_name (str): name of pause storm
        pause_prio_list (list): priorities to pause for PFC frames
        test_flow_name (str): name prefix of test flows
        test_prio_list (list): priorities of test flows
        test_flow_rate_percent (int): rate percentage for each test flow
        bg_flow_name (str): name prefix of background flows
        bg_prio_list (list): priorities of background flows
        bg_flow_rate_percent (int): rate percentage for each background flow
        data_flow_dur_sec (int): duration of data flows in second
        pfc_storm_dur_sec (float): duration of the pause storm in second
        data_pkt_size (int): packet size of data flows in byte
        prio_dscp_map (dict): Priority vs. DSCP map (key = priority).
        traffic_pattern (str): traffic pattern, "many to one" or "all to all"

    Returns:
        N/A
    """

    """ Warm up traffic is initially sent before any other traffic to prevent pfcwd
    fake alerts caused by idle links (non-incremented packet counters) during pfcwd detection periods """
    warm_up_traffic_dur_sec = WARM_UP_TRAFFIC_DUR
    warm_up_traffic_delay_sec = 0
    warm_up_traffic_prio_list = test_flow_prio_list
    warm_up_traffic_rate_percent = test_flow_rate_percent

    """ Generate warm-up traffic """
    __gen_data_flows(testbed_config=testbed_config,
                     port_config_list=port_config_list,
                     src_port_id_list=tx_port_id_list,
                     dst_port_id_list=rx_port_id_list,
                     flow_name_prefix=WARM_UP_TRAFFIC_NAME,
                     flow_prio_list=warm_up_traffic_prio_list,
                     flow_rate_percent=warm_up_traffic_rate_percent,
                     flow_dur_sec=warm_up_traffic_dur_sec,
                     flow_delay_sec=warm_up_traffic_delay_sec,
                     data_pkt_size=data_pkt_size,
                     prio_dscp_map=prio_dscp_map)

    """ Generate a PFC pause storm """
    pause_port_id = rx_port_id_list[0]
    __gen_pause_flow(testbed_config=testbed_config,
                     port_config_list=port_config_list,
                     src_port_id=pause_port_id,
                     flow_name=pause_flow_name,
                     pause_prio_list=pause_prio_list,
                     flow_dur_sec=pfc_storm_dur_sec,
                     flow_delay_sec=WARM_UP_TRAFFIC_DUR)

    """ Generate test flow traffic """
    __gen_data_flows(testbed_config=testbed_config,
                     port_config_list=port_config_list,
                     src_port_id_list=tx_port_id_list,
                     dst_port_id_list=rx_port_id_list,
                     flow_name_prefix=TEST_FLOW_NAME,
                     flow_prio_list=test_flow_prio_list,
                     flow_rate_percent=test_flow_rate_percent,
                     flow_dur_sec=data_flow_dur_sec,
                     flow_delay_sec=WARM_UP_TRAFFIC_DUR,
                     data_pkt_size=data_pkt_size,
                     prio_dscp_map=prio_dscp_map)

    """ Generate background flow traffic """
    __gen_data_flows(testbed_config=testbed_config,
                     port_config_list=port_config_list,
                     src_port_id_list=tx_port_id_list,
                     dst_port_id_list=rx_port_id_list,
                     flow_name_prefix=BG_FLOW_NAME,
                     flow_prio_list=bg_flow_prio_list,
                     flow_rate_percent=bg_flow_rate_percent,
                     flow_dur_sec=data_flow_dur_sec,
                     flow_delay_sec=WARM_UP_TRAFFIC_DUR,
                     data_pkt_size=data_pkt_size,
                     prio_dscp_map=prio_dscp_map)


def __gen_data_flows(testbed_config,
                     port_config_list,
                     src_port_id_list,
                     dst_port_id_list,
                     flow_name_prefix,
                     flow_prio_list,
                     flow_rate_percent,
                     flow_dur_sec,
                     flow_delay_sec,
                     data_pkt_size,
                     prio_dscp_map):
    """
    Generate the configuration for data flows

    Args:
        testbed_config (obj): testbed L1/L2/L3 configuration
        port_config_list (list): list of port configuration
        src_port_id_list (list): IDs of source ports
        dst_port_id_list (list): IDs of destination ports
        flow_name_prefix (str): prefix of flows' names
        flow_prio_list (list): priorities of data flows
        flow_rate_percent (int): rate percentage for each flow
        flow_dur_sec (int): duration of each flow in second
        flow_delay_sec (int): delay before starting pause flow in second
        data_pkt_size (int): packet size of data flows in byte
        prio_dscp_map (dict): Priority vs. DSCP map (key = priority).

    Returns:
        N/A
    """

    for src_port_id in src_port_id_list:
        for dst_port_id in dst_port_id_list:
            if src_port_id == dst_port_id:
                continue

            for prio in flow_prio_list:
                __gen_data_flow(testbed_config=testbed_config,
                                port_config_list=port_config_list,
                                src_port_id=src_port_id,
                                dst_port_id=dst_port_id,
                                flow_name_prefix=flow_name_prefix,
                                flow_prio=prio,
                                flow_rate_percent=flow_rate_percent,
                                flow_dur_sec=flow_dur_sec,
                                flow_delay_sec=flow_delay_sec,
                                data_pkt_size=data_pkt_size,
                                prio_dscp_map=prio_dscp_map)


def __gen_data_flow(testbed_config,
                    port_config_list,
                    src_port_id,
                    dst_port_id,
                    flow_name_prefix,
                    flow_prio,
                    flow_rate_percent,
                    flow_dur_sec,
                    flow_delay_sec,
                    data_pkt_size,
                    prio_dscp_map):
    """
    Generate the configuration for a data flow

    Args:
        testbed_config (obj): testbed L1/L2/L3 configuration
        port_config_list (list): list of port configuration
        src_port_id (int): ID of the source port
        dst_port_id (int): ID of destination port
        flow_name_prefix (str): prefix of flow' name
        flow_prio_list (list): priorities of the flow
        flow_rate_percent (int): rate percentage for the flow
        flow_dur_sec (int): duration of the flow in second
        flow_delay_sec (int): delay before starting pause flow in second
        data_pkt_size (int): packet size of the flow in byte
        prio_dscp_map (dict): Priority vs. DSCP map (key = priority).

    Returns:
        N/A
    """
    tx_port_config = next((x for x in port_config_list if x.id == src_port_id), None)
    rx_port_config = next((x for x in port_config_list if x.id == dst_port_id), None)

    tx_mac = tx_port_config.mac
    if tx_port_config.gateway == rx_port_config.gateway and \
       tx_port_config.prefix_len == rx_port_config.prefix_len:
        """ If soruce and destination port are in the same subnet """
        rx_mac = rx_port_config.mac
    else:
        rx_mac = tx_port_config.gateway_mac

    flow_name = __data_flow_name(name_prefix=flow_name_prefix,
                                 src_id=src_port_id,
                                 dst_id=dst_port_id,
                                 prio=flow_prio)

    flow = testbed_config.flows.flow(flow_name)[-1]

    flow.tx_rx.port.tx_name = testbed_config.ports[src_port_id].name
    flow.tx_rx.port.rx_name = testbed_config.ports[dst_port_id].name

    eth, ipv4, udp = flow.packet.ethernet().ipv4().udp()
    global UDP_SRC_START
    src_port = UDP_SRC_START
    UDP_SRC_START += 1
    udp.src_port.increment.start = src_port
    udp.src_port.increment.step = 1
    udp.src_port.increment.count = 1

    eth.src.value = tx_mac
    eth.dst.value = rx_mac
    if pfcQueueGroupSize == 8:
        eth.pfc_queue.value = flow_prio
    else:
        eth.pfc_queue.value = pfcQueueValueDict[flow_prio]

    ipv4.src.value = tx_port_config.ip
    ipv4.dst.value = gen_data_flow_dest_ip(rx_port_config.ip)
    ipv4.priority.choice = ipv4.priority.DSCP
    ipv4.priority.dscp.phb.values = prio_dscp_map[flow_prio]
    ipv4.priority.dscp.ecn.value = (
        ipv4.priority.dscp.ecn.CAPABLE_TRANSPORT_1)

    flow.size.fixed = data_pkt_size
    flow.rate.percentage = flow_rate_percent
    flow.duration.fixed_seconds.seconds = flow_dur_sec
    flow.duration.fixed_seconds.delay.nanoseconds = int(
        sec_to_nanosec(flow_delay_sec))

    flow.metrics.enable = True
    flow.metrics.loss = True


def __gen_pause_flow(testbed_config,
                     port_config_list,
                     src_port_id,
                     flow_name,
                     pause_prio_list,
                     flow_dur_sec,
                     flow_delay_sec):
    """
    Generate the configuration for a PFC pause storm

    Args:
        testbed_config (obj): testbed L1/L2/L3 configuration
        port_config_list (list): list of port configuration
        src_port_id (int): ID of the source port
        flow_name (str): flow' name
        pause_prio_list (list): priorities to pause for PFC frames
        flow_dur_sec (float): duration of the flow in second
        flow_delay_sec (int): delay before starting pause flow in second

    Returns:
        N/A
    """

    pause_flow = testbed_config.flows.flow(name=flow_name)[-1]
    pause_flow.tx_rx.port.tx_name = testbed_config.ports[src_port_id].name
    pause_flow.tx_rx.port.rx_name = testbed_config.ports[src_port_id].name

    pause_pkt = pause_flow.packet.pfcpause()[-1]

    pause_time = []
    for x in range(8):
        if x in pause_prio_list:
            pause_time.append(int('ffff', 16))
        else:
            pause_time.append(int('0000', 16))

    vector = pfc_class_enable_vector(pause_prio_list)

    pause_pkt.src.value = '00:00:fa:ce:fa:ce'
    pause_pkt.dst.value = '01:80:C2:00:00:01'
    pause_pkt.class_enable_vector.value = vector
    pause_pkt.pause_class_0.value = pause_time[0]
    pause_pkt.pause_class_1.value = pause_time[1]
    pause_pkt.pause_class_2.value = pause_time[2]
    pause_pkt.pause_class_3.value = pause_time[3]
    pause_pkt.pause_class_4.value = pause_time[4]
    pause_pkt.pause_class_5.value = pause_time[5]
    pause_pkt.pause_class_6.value = pause_time[6]
    pause_pkt.pause_class_7.value = pause_time[7]

    """
    The minimal fixed time duration in SNAPPI is 1 second.
    To support smaller durations, we need to use # of packets
    """
    speed_str = testbed_config.layer1[0].speed
    speed_gbps = int(speed_str.split('_')[1])
    pause_dur = 65535 * 64 * 8.0 / (speed_gbps * 1e9)
    pps = int(2 / pause_dur)
    pkt_cnt = pps * flow_dur_sec

    pause_flow.rate.pps = pps
    pause_flow.size.fixed = 64
    pause_flow.duration.fixed_packets.packets = int(pkt_cnt)
    pause_flow.duration.fixed_packets.delay.nanoseconds = 0
    pause_flow.duration.fixed_packets.delay.nanoseconds = int(
        sec_to_nanosec(flow_delay_sec))

    pause_flow.metrics.enable = True
    pause_flow.metrics.loss = True


def __run_traffic(api, config, all_flow_names, exp_dur_sec):
    """
    Run traffic and dump per-flow statistics

    Args:
        api (obj): SNAPPI session
        config (obj): experiment config (testbed config + flow config)
        all_flow_names (list): list of names of all the flows
        exp_dur_sec (int): experiment duration in second

    Returns:
        per-flow statistics (list)
    """
    api.set_config(config)

    logger.info('Wait for Arp to Resolve ...')
    wait_for_arp(api, max_attempts=30, poll_interval_sec=2)

    logger.info('Starting transmit on all flows ...')
    cs = api.control_state()
    cs.traffic.flow_transmit.state = cs.traffic.flow_transmit.START
    api.set_control_state(cs)

    time.sleep(exp_dur_sec)

    attempts = 0
    max_attempts = 20

    while attempts < max_attempts:
        request = api.metrics_request()
        request.flow.flow_names = all_flow_names
        rows = api.get_metrics(request).flow_metrics

        """ If all the data flows have stopped """
        transmit_states = [row.transmit for row in rows]
        if len(rows) == len(all_flow_names) and\
           list(set(transmit_states)) == ['stopped']:
            time.sleep(SNAPPI_POLL_DELAY_SEC)
            break
        else:
            time.sleep(1)
            attempts += 1

    pytest_assert(attempts < max_attempts,
                  "Flows do not stop in {} seconds".format(max_attempts))

    """ Dump per-flow statistics """
    request = api.metrics_request()
    request.flow.flow_names = all_flow_names
    rows = api.get_metrics(request).flow_metrics

    logger.info('Stop transmit on all flows ...')
    cs = api.control_state()
    cs.traffic.flow_transmit.state = cs.traffic.flow_transmit.STOP
    api.set_control_state(cs)

    return rows


def __verify_results(rows,
                     speed_gbps,
                     pause_flow_name,
                     test_flow_name,
                     bg_flow_name,
                     test_flow_rate_percent,
                     bg_flow_rate_percent,
                     data_flow_dur_sec,
                     data_pkt_size,
                     trigger_pfcwd,
                     pause_port_id,
                     rx_deviation,
                     rx_tx_deviations,
                     asic_type):
    """
    Verify if we get expected experiment results

    Args:
        rows (list): per-flow statistics
        speed_gbps (int): link speed in Gbps
        pause_flow_name (str): name of pause storm
        test_flow_name (str): name of test flows
        bg_flow_name (str): name of background flows
        test_flow_rate_percent (int): rate percentage for each test flow
        bg_flow_rate_percent (int): rate percentage for each background flow
        data_pkt_size (int): packet size of data flows in byte
        test_flow_pause (bool): if test flows are expected to be paused
        trigger_pfcwd (bool): if PFC watchdog is expected to be triggered
        pause_port_id (int): ID of the port to send PFC pause frames
        rx_deviation (float): maximum allowable deviation for rx_frames relative to theoretical value
        rx_tx_deviations (list of floats): maximum allowable % deviation for rx_frames relative to tx_frames

    Returns:
        N/A
    """

    """ Check for whether DUT is a Mellanox device """
    is_mlnx_device = True if "mellanox" in asic_type.lower() else False

    for row in rows:
        flow_name = row.name
        tx_frames = row.frames_tx
        rx_frames = row.frames_rx

        logger.info('Flow Name : {} , Tx Frames : {}, Rx Frames : {}'.format(flow_name, tx_frames, rx_frames))

        if pause_flow_name in flow_name:
            """ PFC pause storm """
            logger.info('PFC pause storm expected to be dropped')
            pytest_assert(tx_frames > 0 and rx_frames == 0,
                          "All the PFC packets should be dropped")

        elif bg_flow_name in flow_name:
            """ Background flows """
            logger.info('Background flows expected not to have any dropped packets')
            pytest_assert(tx_frames == rx_frames,
                          '{} should not have any dropped packet'.format(flow_name))

            exp_bg_flow_rx_pkts = bg_flow_rate_percent / 100.0 * speed_gbps \
                * 1e9 * data_flow_dur_sec / 8.0 / data_pkt_size
            deviation = (rx_frames - exp_bg_flow_rx_pkts) / float(exp_bg_flow_rx_pkts)
            pytest_assert(abs(deviation) < rx_deviation,
                          '{} should receive {} packets (actual {})'.
                          format(flow_name, exp_bg_flow_rx_pkts, rx_frames))

        elif test_flow_name in flow_name:
            """ Test flows """
            src_port_id = __data_flow_src(flow_name)
            dst_port_id = __data_flow_dst(flow_name)

            exp_test_flow_rx_pkts = test_flow_rate_percent / 100.0 * speed_gbps \
                * 1e9 * data_flow_dur_sec / 8.0 / data_pkt_size

            if trigger_pfcwd and dst_port_id == pause_port_id:
                """ Once PFC watchdog is triggered, it will impact bi-directional traffic """
                logger.info('Once PFC watchdog is triggered, it will impact bi-directional traffic')
                logger.info('Tx and Rx should have dropped packets')
                pytest_assert(tx_frames > rx_frames,
                              '{} should have dropped packets'.format(flow_name))
            elif trigger_pfcwd and src_port_id == pause_port_id:
                if is_mlnx_device:
                    """ During a pfc storm with pfcwd triggered, Mellanox devices do not drop Rx packets """
                    pytest_assert(tx_frames == rx_frames,
                                  '{} should not have dropped packets for Mellanox device'.format(flow_name))
            elif not trigger_pfcwd and dst_port_id == pause_port_id:
                """ This test flow is delayed by PFC storm """
                logger.info('This test flow is delayed by PFC storm')
                logger.info('Tx and Rx should not have any dropped packet')
                pytest_assert(tx_frames == rx_frames,
                              '{} should not have any dropped packet'.format(flow_name))
                pytest_assert(rx_frames < exp_test_flow_rx_pkts,
                              '{} shoudl receive less than {} packets (actual {})'.
                              format(flow_name, exp_test_flow_rx_pkts, rx_frames))

            else:
                for dev_pct in rx_tx_deviations:
                    """ Otherwise, the test flow is not impacted by PFC storm """
                    pytest_assert(abs(tx_frames - rx_frames)/float(tx_frames) < dev_pct,
                                  '{} should be within {} percent deviation'.format(flow_name, dev_pct*100))

                deviation = (rx_frames - exp_test_flow_rx_pkts) / float(exp_test_flow_rx_pkts)
                pytest_assert(abs(deviation) < rx_deviation,
                              '{} should receive {} packets (actual {})'.
                              format(flow_name, exp_test_flow_rx_pkts, rx_frames))
