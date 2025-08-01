

def _port_alias_to_name_map_50G(all_ports, s100G_ports,):
    new_map = {}
    # 50G ports
    s50G_ports = list(set(all_ports) - set(s100G_ports))

    for i in s50G_ports:
        new_map["Ethernet%d/1" % i] = "Ethernet%d" % ((i - 1) * 4)
        new_map["Ethernet%d/3" % i] = "Ethernet%d" % ((i - 1) * 4 + 2)

    for i in s100G_ports:
        new_map["Ethernet%d/1" % i] = "Ethernet%d" % ((i - 1) * 4)

    return new_map


def get_port_alias_to_name_map(hwsku, asic_name=None):
    port_alias_to_name_map = {}
    port_alias_asic_map = {}
    port_name_to_index_map = {}
    HWSKU_WITH_PORT_INDEX_FROM_PORT_CONFIG = ["Cisco-88-LC0-36FH-M-O36",
                                              "Cisco-88-LC0-36FH-O36",
                                              "Cisco-8800-LC-48H-C48"]
    try:
        from sonic_py_common import multi_asic
        from ansible.module_utils.multi_asic_utils import load_db_config
        load_db_config()
        ports_info = multi_asic.get_port_table(namespace=asic_name)
        for port, port_data in ports_info.items():
            if "alias" in port_data:
                port_alias_to_name_map[port_data["alias"]] = port
            if "asic_port_name" in port_data:
                port_alias_asic_map[port_data["asic_port_name"]] = port
            if "index" in port_data and hwsku in HWSKU_WITH_PORT_INDEX_FROM_PORT_CONFIG:
                port_name_to_index_map[port] = int(port_data["index"])
    except ImportError:
        if hwsku == "Force10-S6000":
            for i in range(0, 128, 4):
                port_alias_to_name_map["fortyGigE0/%d" % i] = "Ethernet%d" % i
        elif hwsku == "Force10-S6100":
            for i in range(0, 4):
                for j in range(0, 16):
                    port_alias_to_name_map["fortyGigE1/%d/%d" % (i + 1, j + 1)] = "Ethernet%d" % (i * 16 + j)
        elif hwsku in ["Force10-Z9100", "Force10-Z9100-C32", "DellEMC-S5232f-C32"]:
            for i in range(0, 128, 4):
                port_alias_to_name_map["hundredGigE1/%d" % (i / 4 + 1)] = "Ethernet%d" % i
        # TODO: Come up with a generic formula for generating etp style aliases based on number of ports and lanes
        elif hwsku == "DellEMC-Z9332f-M-O16C64":
            # 100G ports
            s100G_ports = [x for x in range(0, 96, 2)] + [x for x in range(128, 160, 2)]

            # 400G ports
            s400G_ports = [x for x in range(96, 128, 8)] + [x for x in range(160, 256, 8)]

            # 10G ports
            s10G_ports = [x for x in range(256, 258)]

            for i in s100G_ports:
                alias = "etp{}{}".format(((i + 8) // 8), chr(ord('a') + (i // 2) % 4))
                port_alias_to_name_map[alias] = "Ethernet{}".format(i)
            for i in s400G_ports:
                alias = "etp{}".format((i // 8) + 1)
                port_alias_to_name_map[alias] = "Ethernet{}".format(i)
            for i in s10G_ports:
                alias = "etp{}".format(33 if i == 256 else 34)
                port_alias_to_name_map[alias] = "Ethernet{}".format(i)
        elif hwsku == "DellEMC-Z9332f-O32" or hwsku == "DellEMC-Z9332f-C32":
            for i in range(0, 256, 8):
                alias = "etp{}".format((i // 8) + 1)
                port_alias_to_name_map[alias] = "Ethernet{}".format(i)
            for i in range(256, 258):
                alias = "etp{}".format(33 if i == 256 else 34)
                port_alias_to_name_map[alias] = "Ethernet{}".format(i)
        elif hwsku == "Arista-7050-QX32":
            for i in range(1, 25):
                port_alias_to_name_map["Ethernet%d/1" % i] = "Ethernet%d" % ((i - 1) * 4)
            for i in range(25, 33):
                port_alias_to_name_map["Ethernet%d" % i] = "Ethernet%d" % ((i - 1) * 4)
        elif hwsku == "Arista-7050-QX-32S" or hwsku == "Arista-7050QX-32S-S4Q31":
            for i in range(0, 4):
                port_alias_to_name_map["Ethernet%d" % (i + 1)] = "Ethernet%d" % i
            for i in range(6, 29):
                port_alias_to_name_map["Ethernet%d/1" % i] = "Ethernet%d" % ((i - 5) * 4)
            for i in range(29, 37):
                port_alias_to_name_map["Ethernet%d" % i] = "Ethernet%d" % ((i - 5) * 4)
        elif hwsku == "Arista-7050QX32S-Q32":
            for i in range(5, 29):
                port_alias_to_name_map["Ethernet%d/1" % i] = "Ethernet%d" % ((i - 5) * 4)
            for i in range(29, 37):
                port_alias_to_name_map["Ethernet%d" % i] = "Ethernet%d" % ((i - 5) * 4)
        elif hwsku == "Arista-7280CR3-C40":
            for i in range(1, 33):
                port_alias_to_name_map["Ethernet%d/1" % i] = "Ethernet%d" % ((i - 1) * 4)
            for i in range(33, 41, 2):
                port_alias_to_name_map["Ethernet%d/1" % i] = "Ethernet%d" % ((i - 1) * 4)
                port_alias_to_name_map["Ethernet%d/5" % i] = "Ethernet%d" % (i * 4)
        elif hwsku == "Arista-7260CX3-C64" or hwsku == "Arista-7170-64C" or hwsku == "Arista-7260CX3-Q64":
            for i in range(1, 65):
                port_alias_to_name_map["Ethernet%d/1" % i] = "Ethernet%d" % ((i - 1) * 4)
        elif hwsku == "Arista-7060CX-32S-C32" or hwsku == "Arista-7060CX-32S-Q32" \
                or hwsku == "Arista-7060CX-32S-C32-T1" or hwsku == "Arista-7170-32CD-C32" \
                or hwsku == "Arista-7050CX3-32S-C28S4" \
                or hwsku == "Arista-7050CX3-32S-C32" \
                or hwsku == "Arista-7050CX3-32C-C32":
            for i in range(1, 33):
                port_alias_to_name_map["Ethernet%d/1" % i] = "Ethernet%d" % ((i - 1) * 4)
        elif hwsku in ["Arista-7060DX5-64S"]:
            for i in range(1, 65):
                port_alias_to_name_map["Ethernet%d/1" % i] = "Ethernet%d" % ((i - 1) * 8)
        elif hwsku in ["Arista-7060X6-64DE", "Arista-7060X6-64DE-64x400G",
                       "Arista-7060X6-64PE", "Arista-7060X6-64PE-64x400G",
                       "Arista-7060X6-64PE-P64", "Arista-7060X6-64PE-B-P64"]:
            for i in range(1, 65):
                port_alias_to_name_map["etp%d" % i] = "Ethernet%d" % ((i - 1) * 8)
            port_alias_to_name_map["etp65"] = "Ethernet512"
            port_alias_to_name_map["etp66"] = "Ethernet513"
        elif hwsku in ["Arista-7060X6-64DE-O128S2", "Arista-7060X6-64PE-O128S2", "Arista-7060X6-64PE-B-O128",
                       "Arista-7060X6-64PE-B-O128S2"]:
            split_alias_list = ["a", "b"]
            for i in range(1, 65):
                for j, split_alias in enumerate(split_alias_list):
                    alias = "etp{}{}".format(i, split_alias)
                    port_alias_to_name_map[alias] = "Ethernet%d" % ((i - 1) * 8 + j * 4)
            if hwsku not in ["Arista-7060X6-64PE-B-O128"]:
                port_alias_to_name_map["etp65"] = "Ethernet512"
                port_alias_to_name_map["etp66"] = "Ethernet513"
        elif hwsku in ["Arista-7060X6-64PE-B-P32O64", "Arista-7060X6-64PE-P32O64"]:
            for i in range(1, 33):
                port_alias_to_name_map["etp%d" % (i)] = "Ethernet%d" % ((i - 1) * 8)
            for i in range(33, 65):
                for x, j in zip([1, 5], ["a", "b"]):
                    port_alias_to_name_map["etp%d%s" % (i, j)] = "Ethernet%d" % ((i - 1) * 8 + x - 1)
            port_alias_to_name_map["etp65"] = "Ethernet512"
            port_alias_to_name_map["etp66"] = "Ethernet513"
        elif hwsku == "Arista-7060X6-64PE-256x200G":
            for i in range(1, 65):
                for j in [1, 3, 5, 7]:
                    port_alias_to_name_map["Ethernet%d/%d" % (i, j)] = "Ethernet%d" % ((i - 1) * 8 + j - 1)
            port_alias_to_name_map["Ethernet65"] = "Ethernet512"
            port_alias_to_name_map["Ethernet66"] = "Ethernet513"
        elif hwsku == "Arista-7060X6-64PE-C256S2":
            for i in range(1, 65, 2):  # This hwsku uses every second OSFP port.
                for j in range(1, 9):
                    port_alias_to_name_map["Ethernet%d/%d" % (i, j)] = "Ethernet%d" % ((i - 1) * 8 + j - 1)
            port_alias_to_name_map["Ethernet65"] = "Ethernet512"
            port_alias_to_name_map["Ethernet66"] = "Ethernet513"
        elif hwsku == "Arista-7060X6-64PE-C224O8":  # This hwsku uses every second OSFP port.
            for i in range(1, 65, 2):
                if i in [13, 17, 45, 49]:
                    for j in [1, 5]:
                        port_alias_to_name_map["Ethernet%d/%d" % (i, j)] = "Ethernet%d" % ((i - 1) * 8 + j - 1)
                else:
                    for j in range(1, 9):
                        port_alias_to_name_map["Ethernet%d/%d" % (i, j)] = "Ethernet%d" % ((i - 1) * 8 + j - 1)
            port_alias_to_name_map["Ethernet65"] = "Ethernet512"
            port_alias_to_name_map["Ethernet66"] = "Ethernet513"
        elif hwsku == "Arista-7060X6-64PE-B-C512S2":
            split_alias_list = ["a", "b", "c", "d", "e", "f", "g", "h"]
            for i in range(1, 65):
                for idx, split_alias in enumerate(split_alias_list):
                    alias = "etp{}{}".format(i, split_alias)
                    eth_name = "Ethernet{}".format((i - 1) * 8 + idx)
                    port_alias_to_name_map[alias] = eth_name
            port_alias_to_name_map['etp65'] = "Ethernet512"
            port_alias_to_name_map['etp66'] = "Ethernet513"
        elif hwsku == "Arista-7060X6-64PE-B-C448O16":
            split_alias_list = ["a", "b", "c", "d", "e", "f", "g", "h"]
            split_alias_list_1 = ["a", "b"]
            split_2_port_indexs = [13, 14, 17, 18, 45, 46, 49, 50]
            for i in range(1, 65):
                if i in split_2_port_indexs:
                    for idx, split_alias in enumerate(split_alias_list_1):
                        alias = "etp{}{}".format(i, split_alias)
                        eth_name = "Ethernet{}".format((i - 1) * 8 + idx * 4)
                        port_alias_to_name_map[alias] = eth_name
                else:
                    for idx, split_alias in enumerate(split_alias_list):
                        alias = "etp{}{}".format(i, split_alias)
                        eth_name = "Ethernet{}".format((i - 1) * 8 + idx)
                        port_alias_to_name_map[alias] = eth_name
        elif hwsku in ["Arista-7060X6-16PE-384C-O128S2", "Arista-7060X6-16PE-384C-B-O128S2",
                       "Arista-7060X6-16PE-384C-B-O128S2-COPPER-LAB", "Arista-7060X6-16PE-384C-B-O128S2-LAB",
                       "Arista-7060X6-16PE-384C-O128S2-COPPER-LAB", "Arista-7060X6-16PE-384C-O128S2-LAB"]:
            split_alias_list = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l"]
            split_alias_list_1 = ["a", "b"]
            split_2_port_indexs = list(range(1, 17))
            cur_idx = 0
            for i in range(1, 25):
                if i in split_2_port_indexs:
                    for idx, split_alias in enumerate(split_alias_list_1):
                        alias = "etp{}{}".format(i, split_alias)
                        eth_name = "Ethernet{}".format(cur_idx)
                        port_alias_to_name_map[alias] = eth_name
                        cur_idx += 4
                else:
                    for idx, split_alias in enumerate(split_alias_list):
                        alias = "etp{}{}".format(i, split_alias)
                        eth_name = "Ethernet{}".format(cur_idx)
                        port_alias_to_name_map[alias] = eth_name
                        cur_idx += 4
            port_alias_to_name_map['etp25a'] = "Ethernet512"
            port_alias_to_name_map['etp25b'] = "Ethernet513"
        elif hwsku == "Arista-7050QX32S-Q32":
            for i in range(5, 29):
                port_alias_to_name_map["Ethernet%d/1" % i] = "Ethernet%d" % ((i - 5) * 4)
            for i in range(29, 37):
                port_alias_to_name_map["Ethernet%d" % i] = "Ethernet%d" % ((i - 5) * 4)
        elif hwsku == "Mellanox-SN2700-D40C8S8":
            # 10G ports
            s10G_ports = list(range(0, 4)) + list(range(8, 12))

            # 50G ports
            s50G_ports = [x for x in range(16, 24, 2)] + [x for x in range(40, 88, 2)] + [x for x in range(104, 128, 2)]

            # 100G ports
            s100G_ports = [x for x in range(24, 40, 4)] + [x for x in range(88, 104, 4)]

            for i in s10G_ports:
                alias = "etp%d" % (i / 4 + 1) + chr(ord('a') + i % 4)
                port_alias_to_name_map[alias] = "Ethernet%d" % i
            for i in s50G_ports:
                alias = "etp%d" % (i / 4 + 1) + ("a" if i % 4 == 0 else "b")
                port_alias_to_name_map[alias] = "Ethernet%d" % i
            for i in s100G_ports:
                alias = "etp%d" % (i / 4 + 1)
                port_alias_to_name_map[alias] = "Ethernet%d" % i
        elif hwsku == "Mellanox-SN2700-D44C10":
            # 50G ports
            s50G_ports = [x for x in range(8, 24, 2)] + [x for x in range(40, 88, 2)] + [x for x in range(104, 128, 2)]

            # 100G ports
            s100G_ports = [0, 4] + [x for x in range(24, 40, 4)] + [x for x in range(88, 104, 4)]

            for i in s50G_ports:
                alias = "etp%d" % (i / 4 + 1) + ("a" if i % 4 == 0 else "b")
                port_alias_to_name_map[alias] = "Ethernet%d" % i
            for i in s100G_ports:
                alias = "etp%d" % (i / 4 + 1)
                port_alias_to_name_map[alias] = "Ethernet%d" % i
        elif hwsku == "Mellanox-SN2700-D48C8":
            # 50G ports
            s50G_ports = [x for x in range(0, 24, 2)] + [x for x in range(40, 88, 2)] + [x for x in range(104, 128, 2)]

            # 100G ports
            s100G_ports = [x for x in range(24, 40, 4)] + [x for x in range(88, 104, 4)]

            for i in s50G_ports:
                alias = "etp%d" % (i / 4 + 1) + ("a" if i % 4 == 0 else "b")
                port_alias_to_name_map[alias] = "Ethernet%d" % i
            for i in s100G_ports:
                alias = "etp%d" % (i / 4 + 1)
                port_alias_to_name_map[alias] = "Ethernet%d" % i
        elif hwsku == "Mellanox-SN3800-D112C8":
            x_ports = [x for x in range(0, 95, 2)]
            for i in x_ports:
                alias = "etp%d" % (i / 4 + 1) + ("a" if i % 4 == 0 else "b")
                # print alias, "Ethernet%d" % i
                port_alias_to_name_map[alias] = "Ethernet%d" % i
            x_ports = [x for x in range(96, 101, 4)] + [x for x in range(104, 111, 2)] +\
                [x for x in range(112, 117, 4)] + [x for x in range(120, 127, 2)] + [x for x in range(128, 133, 4)] +\
                [x for x in range(136, 143, 2)] + [x for x in range(144, 149, 4)] + [x for x in range(152, 159, 2)]
            i = 0
            while i < len(x_ports):
                for j in range(0, 2):
                    alias = "etp%d" % (x_ports[i] / 4 + 1)
                    port_alias_to_name_map[alias] = "Ethernet%d" % x_ports[i]
                    # print alias, "Ethernet%d" % ports[i]
                    i += 1
                for j in range(0, 2):
                    alias = "etp%d" % (x_ports[i] / 4 + 1) + "a"
                    port_alias_to_name_map[alias] = "Ethernet%d" % x_ports[i]
                    # print alias, "Ethernet%d" % ports[i]
                    i += 1
                    alias = "etp%d" % (x_ports[i] / 4 + 1) + "b"
                    port_alias_to_name_map[alias] = "Ethernet%d" % x_ports[i]
                    # print alias, "Ethernet%d" % ports[i]
                    i += 1
            x_ports = [x for x in range(160, 255, 2)]
            for i in x_ports:
                alias = "etp%d" % (i / 4 + 1) + ("a" if i % 4 == 0 else "b")
                # print alias, "Ethernet%d" % i
                port_alias_to_name_map[alias] = "Ethernet%d" % i
        elif hwsku in ["Mellanox-SN2700-C28D8", "Mellanox-SN2700-A1-C28D8"]:
            # 50G ports
            s50G_ports = [x for x in range(112, 127, 2)]

            # 100G ports
            s100G_ports = [x for x in range(0, 109, 4)]

            for i in s50G_ports:
                alias = "etp%d" % (i / 4 + 1) + ("a" if i % 4 == 0 else "b")
                port_alias_to_name_map[alias] = "Ethernet%d" % i
            for i in s100G_ports:
                alias = "etp%d" % (i / 4 + 1)
                port_alias_to_name_map[alias] = "Ethernet%d" % i
        elif hwsku in ["ACS-MSN3800", "ACS-MSN4600C", 'Mellanox-SN4700-V64']:
            for i in range(1, 65):
                port_alias_to_name_map["etp%d" % i] = "Ethernet%d" % ((i - 1) * 4)
        elif hwsku == "Mellanox-SN2700" or hwsku == "ACS-MSN2700":
            for i in range(1, 33):
                port_alias_to_name_map["etp%d" % i] = "Ethernet%d" % ((i - 1) * 4)
        elif hwsku in ["Arista-7060CX-32S-D48C8", "Arista-7050CX3-32S-D48C8"]:
            # All possible breakout 50G port numbers:
            all_ports = [x for x in range(1, 33)]

            # 100G ports
            s100G_ports = [x for x in range(7, 11)]
            s100G_ports += [x for x in range(23, 27)]

            port_alias_to_name_map = _port_alias_to_name_map_50G(all_ports, s100G_ports)
        elif hwsku == "Arista-7050CX3-32S-S128":
            for i in range(1, 33):
                for j in range(1, 5):
                    port_alias_to_name_map["Ethernet%d/%d" % (i, j)] = "Ethernet%d" % ((i - 1) * 4 + j - 1)
            port_alias_to_name_map["Ethernet33"] = "Ethernet128"
        elif hwsku == "Arista-7050CX3-32S-C6S104":
            for i in range(1, 27):
                for j in range(1, 5):
                    port_alias_to_name_map["Ethernet%d/%d" % (i, j)] = "Ethernet%d" % ((i - 1) * 4 + j - 1)
            for i in range(27, 33):
                port_alias_to_name_map["Ethernet%d/1" % i] = "Ethernet%d" % ((i - 1) * 4)
            port_alias_to_name_map["Ethernet33"] = "Ethernet128"
        elif hwsku == "Arista-7050CX3-32S-C28S16":
            for i in range(1, 5):
                for j in range(1, 5):
                    port_alias_to_name_map["Ethernet%d/%d" % (i, j)] = "Ethernet%d" % ((i - 1) * 4 + j - 1)
            for i in range(5, 33):
                port_alias_to_name_map["Ethernet%d/1" % i] = "Ethernet%d" % ((i - 1) * 4)
            port_alias_to_name_map["Ethernet33"] = "Ethernet128"
        elif hwsku in ["Arista-7260CX3-D108C8", "Arista-7260CX3-D108C8-AILAB",
                       "Arista-7260CX3-D108C8-CSI", "Arista-7260CX3-D108C10"]:
            # All possible breakout 50G port numbers:
            all_ports = [x for x in range(1, 65)]

            # 100G ports
            s100G_ports = [x for x in range(13, 21)]
            if hwsku == "Arista-7260CX3-D108C10":
                # The first 2 ports are 100G
                s100G_ports.extend([x for x in range(1, 3)])
            elif hwsku == "Arista-7260CX3-D108C8-AILAB":
                s100G_ports = [x for x in range(45, 53)]
            elif hwsku == "Arista-7260CX3-D108C8-CSI":
                # Treat 40G port as 100G ports
                s100G_ports = [x for x in range(45, 53)] + [64]

            port_alias_to_name_map = _port_alias_to_name_map_50G(all_ports, s100G_ports)
        elif hwsku in ["Arista-7800R3-48CQ2-C48", "Arista-7800R3-48CQM2-C48"]:
            for i in range(1, 49):
                port_alias_to_name_map["Ethernet%d/1" % i] = "Ethernet%d" % ((i - 1) * 4)
        elif hwsku in ["Arista-7280DR3A-36",
                       "Arista-7280DR3AK-36",
                       "Arista-7280DR3AK-36S",
                       "Arista-7280DR3AM-36",
                       "Arista-7800R3A-36DM2-C36",
                       "Arista-7800R3AK-36DM2-C36",
                       "Arista-7800R3A-36DM2-D36"]:
            for i in range(1, 37):
                sonic_name = "Ethernet%d" % ((i - 1) * 8)
                port_alias_to_name_map["Ethernet{}/{}".format(i, 1)] = sonic_name
        elif hwsku == "Arista-7800R3A-36DM2-C72" or\
                hwsku == "Arista-7800R3A-36D-C72" or\
                hwsku == "Arista-7800R3A-36P-C72" or\
                hwsku == "Arista-7800R3AK-36DM2-C72" or\
                hwsku == "Arista-7800R3AK-36D2-C72" or\
                hwsku == "Arista-7800R3A-36D2-C72":

            intf_idx = 0
            for i in range(1, 37):
                for j in [1, 5]:
                    port_alias_to_name_map["Ethernet%d/%d" % (i, j)] = "Ethernet%d" % intf_idx
                    intf_idx += 4
        elif hwsku == "INGRASYS-S9100-C32":
            for i in range(1, 33):
                port_alias_to_name_map["Ethernet%d/1" % i] = "Ethernet%d" % ((i - 1) * 4)
        elif hwsku == "INGRASYS-S9100-C32" or hwsku == "INGRASYS-S9130-32X" or hwsku == "INGRASYS-S8810-32Q":
            for i in range(1, 33):
                port_alias_to_name_map["Ethernet%d/1" % i] = "Ethernet%d" % ((i - 1) * 4)
        elif hwsku == "INGRASYS-S8900-54XC":
            for i in range(1, 49):
                port_alias_to_name_map["Ethernet%d" % i] = "Ethernet%d" % (i - 1)
            for i in range(49, 55):
                port_alias_to_name_map["Ethernet%d/1" % i] = "Ethernet%d" % ((i - 49) * 4 + 48)
        elif hwsku == "INGRASYS-S8900-64XC":
            for i in range(1, 49):
                port_alias_to_name_map["Ethernet%d" % i] = "Ethernet%d" % (i - 1)
            for i in range(49, 65):
                port_alias_to_name_map["Ethernet%d/1" % i] = "Ethernet%d" % ((i - 49) * 4 + 48)
        elif hwsku == "Accton-AS7712-32X":
            for i in range(1, 33):
                port_alias_to_name_map["hundredGigE%d" % i] = "Ethernet%d" % ((i - 1) * 4)
        elif hwsku == "Accton-AS7726-32X":
            for i in range(1, 33):
                port_alias_to_name_map["hundredGigE%d" % i] = "Ethernet%d" % ((i - 1) * 4)
        elif hwsku == "montara":
            for i in range(1, 33):
                port_alias_to_name_map["hundredGigE%d" % i] = "Ethernet%d" % ((i - 1) * 4)
        elif hwsku == "Celestica-DX010-C32":
            for i in range(1, 33):
                port_alias_to_name_map["etp%d" % i] = "Ethernet%d" % ((i - 1) * 4)
        elif hwsku == "Celestica-DX010-D48C8":
            for i in range(1, 21):
                port_alias_to_name_map["etp{}{}".format((i + 1)//2, "a" if i % 2 == 1 else "b")] = \
                    "Ethernet%d" % ((i - 1) * 2)
            for i in range(21, 25):
                port_alias_to_name_map["etp{}".format(i - 10)] = "Ethernet%d" % ((i - 10 - 1) * 4)
            for i in range(25, 33):
                port_alias_to_name_map["etp{}{}".format((i + 4 + 1)//2, "a" if i % 2 == 1 else "b")] = \
                    "Ethernet%d" % ((i + 4 - 1) * 2)
            for i in range(33, 37):
                port_alias_to_name_map["etp{}".format(i - 14)] = "Ethernet%d" % ((i - 14 - 1) * 4)
            for i in range(37, 57):
                port_alias_to_name_map["etp{}{}".format((i + 8 + 1)//2, "a" if i % 2 == 1 else "b")] = \
                    "Ethernet%d" % ((i + 8 - 1) * 2)
        elif hwsku == "Seastone-DX010":
            for i in range(1, 33):
                port_alias_to_name_map["Eth%d" % i] = "Ethernet%d" % ((i - 1) * 4)
        elif hwsku in ["Celestica-E1031-T48S4", "Nokia-7215", "Nokia-M0-7215", "Nokia-7215-A1"]:
            for i in range(1, 53):
                port_alias_to_name_map["etp%d" % i] = "Ethernet%d" % ((i - 1))
        elif hwsku == "et6448m":
            for i in range(0, 52):
                port_alias_to_name_map["Ethernet%d" % i] = "Ethernet%d" % i
        elif hwsku in ["rd98DX35xx_cn9131", "rd98DX35xx"]:
            for i in range(0, 32):
                port_alias_to_name_map["oneGigE%d" % i] = "Ethernet%d" % i
            for i in range(32, 48):
                port_alias_to_name_map["twod5GigE%d" % i] = "Ethernet%d" % i
            for i in range(48, 54):
                port_alias_to_name_map["twenty5GigE%d" % i] = "Ethernet%d" % i
        elif hwsku in ["Nokia-IXR7250E-36x400G", "Nokia-IXR7250E-36x100G", "Nokia-IXR7250-X3B"]:
            for i in range(1, 37):
                sonic_name = "Ethernet%d" % ((i - 1) * 8)
                port_alias_to_name_map["Ethernet{}/{}".format(i, 1)] = sonic_name
        elif hwsku == 'Nokia-IXR7250E-SUP-10':
            port_alias_to_name_map = {}
        elif hwsku == "newport":
            for i in range(0, 256, 8):
                port_alias_to_name_map["Ethernet%d" % i] = "Ethernet%d" % i
        elif hwsku == "32x100Gb":
            for i in range(0, 32):
                port_alias_to_name_map["Ethernet%d" % i] = "Ethernet%d" % i
        elif hwsku == "36x100Gb":
            for i in range(0, 36):
                port_alias_to_name_map["Ethernet%d" % i] = "Ethernet%d" % i
        elif hwsku == "Cisco-8102-C64":
            for i in range(0, 64):
                port_alias_to_name_map["etp%d" % i] = "Ethernet%d" % (i * 4)
        elif hwsku in ["Cisco-8101-O32", "Cisco-8111-C32", "Cisco-8111-O32"]:
            for i in range(0, 32):
                port_alias_to_name_map["etp%d" % i] = "Ethernet%d" % (i * 8)
        elif hwsku in ["Cisco-8111-O64"]:
            for i in range(0, 64):
                port_alias_to_name_map["etp%d" % i] = "Ethernet%d" % (i * 4)
        elif hwsku in ["Cisco-8101-O8C48", "Cisco-8101-O8V48"]:
            for i in range(0, 12):
                port_alias_to_name_map["etp%da" % i] = "Ethernet%d" % (i * 4 * 2)
                port_alias_to_name_map["etp%db" % i] = "Ethernet%d" % ((i * 4 * 2) + 4)
            for i in range(12, 20):
                port_alias_to_name_map["etp%d" % i] = "Ethernet%d" % (i * 8)
            for i in range(20, 32):
                port_alias_to_name_map["etp%da" % i] = "Ethernet%d" % (i * 4 * 2)
                port_alias_to_name_map["etp%db" % i] = "Ethernet%d" % ((i * 4 * 2) + 4)
        elif hwsku in ["Cisco-8101-C64", "Cisco-8101-V64"]:
            for i in range(0, 32):
                port_alias_to_name_map["etp%da" % i] = "Ethernet%d" % (i * 4 * 2)
                port_alias_to_name_map["etp%db" % i] = "Ethernet%d" % ((i * 4 * 2) + 4)
        elif hwsku in ["Cisco-8122-O64", 'Cisco-8122-O64S2']:
            for i in range(0, 64):
                port_alias_to_name_map["etp%d" % i] = "Ethernet%d" % (i * 8)
        elif hwsku in ["Cisco-8122-O128"]:
            for i in range(0, 64):
                port_alias_to_name_map["etp%da" % i] = "Ethernet%d" % (i * 4 * 2)
                port_alias_to_name_map["etp%db" % i] = "Ethernet%d" % ((i * 4 * 2) + 4)
        elif hwsku in ["Cisco-8800-LC-48H-C48"]:
            for i in range(0, 48, 1):
                port_alias_to_name_map["Ethernet%d" % i] = "Ethernet%d" % (i * 4)
        elif hwsku in ["Cisco-88-LC0-36FH-M-O36", "Cisco-88-LC0-36FH-O36"]:
            for i in range(0, 36, 1):
                port_alias_to_name_map["Ethernet%d" % i] = "Ethernet%d" % (i * 8)
        elif hwsku in ["msft_multi_asic_vs", "Nexus-3164"]:
            for i in range(1, 65):
                port_alias_to_name_map["Ethernet1/%d" % i] = "Ethernet%d" % ((i - 1) * 4)
        elif hwsku in ["Nexus-3132-GE-Q32", "Nexus-3132-GX-Q32"]:
            for i in range(1, 33):
                port_alias_to_name_map["Ethernet1/%d" % i] = "Ethernet%d" % ((i - 1) * 4)
        elif hwsku == "Arista-7260QX-64":
            for i in range(1, 67):
                port_alias_to_name_map["Et%d" % i] = "Ethernet%d" % i
        elif hwsku == "msft_four_asic_vs":
            for i in range(1, 9):
                port_alias_to_name_map["Ethernet1/%d" % i] = "Ethernet%d" % ((i - 1) * 4)
        elif hwsku == "B6510-48VS8CQ" or hwsku == "RA-B6510-48V8C":
            for i in range(1, 49):
                port_alias_to_name_map["twentyfiveGigE0/%d" % i] = "Ethernet%d" % i
            for i in range(49, 57):
                port_alias_to_name_map["hundredGigE0/%d" % (i-48)] = "Ethernet%d" % i
        elif hwsku == "RA-B6510-32C":
            for i in range(1, 33):
                port_alias_to_name_map["hundredGigE%d" % i] = "Ethernet%d" % i
        elif hwsku == "RA-B6910-64C":
            for i in range(1, 65):
                port_alias_to_name_map["hundredGigE%d" % i] = "Ethernet%d" % i
        elif hwsku == "RA-B6920-4S":
            for i in range(1, 129):
                port_alias_to_name_map["hundredGigE%d" % i] = "Ethernet%d" % i
        elif hwsku in ["Wistron_sw_to3200k_32x100", "Wistron_sw_to3200k"]:
            for i in range(0, 256, 8):
                port_alias_to_name_map["Ethernet%d" % i] = "Ethernet%d" % i
        elif hwsku in ["dbmvtx9180_64x100G"]:
            for i in range(0, 505, 8):
                port_alias_to_name_map["Ethernet%d" % i] = "Ethernet%d" % i
        elif hwsku == "Arista-720DT-48S" or hwsku == "Arista-720DT-G48S4":
            for i in range(1, 53):
                port_alias_to_name_map["etp%d" % i] = "Ethernet%d" % (i - 1)
        elif hwsku in ["Mellanox-SN4700-O8C48", "Mellanox-SN4700-O8V48"]:
            idx = 0
            for i in range(1, 13):
                port_alias_to_name_map["etp%da" % i] = "Ethernet%d" % idx
                idx += 4
                port_alias_to_name_map["etp%db" % i] = "Ethernet%d" % idx
                idx += 4
            for i in range(13, 21):
                port_alias_to_name_map["etp%d" % i] = "Ethernet%d" % idx
                idx += 8
            for i in range(21, 33):
                port_alias_to_name_map["etp%da" % i] = "Ethernet%d" % idx
                idx += 4
                port_alias_to_name_map["etp%db" % i] = "Ethernet%d" % idx
                idx += 4
        elif hwsku in ["Mellanox-SN4700-O28", "Mellanox-SN4700-O32", "ACS-SN4280", "Mellanox-SN4280-O28"]:
            idx = 0
            for i in range(1, 33):
                port_alias_to_name_map["etp%d" % i] = "Ethernet%d" % idx
                idx += 8
        elif hwsku in ["Mellanox-SN4280-O8C40", "Mellanox-SN4280-O8V40", "Mellanox-SN4280-C48"]:
            idx = 0
            for i in range(1, 13):
                port_alias_to_name_map["etp%da" % i] = "Ethernet%d" % idx
                idx += 4
                port_alias_to_name_map["etp%db" % i] = "Ethernet%d" % idx
                idx += 4
            for i in range(13, 21):
                port_alias_to_name_map["etp%d" % i] = "Ethernet%d" % idx
                idx += 8
            for i in range(21, 29):
                port_alias_to_name_map["etp%da" % i] = "Ethernet%d" % idx
                idx += 4
                port_alias_to_name_map["etp%db" % i] = "Ethernet%d" % idx
                idx += 4
            for i in range(29, 33):
                port_alias_to_name_map["etp%d" % i] = "Ethernet%d" % idx
                idx += 8
        elif hwsku == "Mellanox-SN5600-V256":
            split_alias_list = ["a", "b", "c", "d"]
            for i in range(1, 65):
                for idx, split_alias in enumerate(split_alias_list):
                    alias = "etp{}{}".format(i, split_alias)
                    eth_name = "Ethernet{}".format((i - 1) * 8 + idx * 2)
                    port_alias_to_name_map[alias] = eth_name
        elif hwsku in ["Mellanox-SN5600-C256S1", "Mellanox-SN5610N-C256S2"]:
            split_alias_list = ["a", "b", "c", "d", "e", "f", "g", "h"]
            for i in range(1, 65, 2):
                for idx, split_alias in enumerate(split_alias_list):
                    alias = "etp{}{}".format(i, split_alias)
                    eth_name = "Ethernet{}".format((i - 1) * 8 + idx)
                    port_alias_to_name_map[alias] = eth_name
            port_alias_to_name_map['etp65'] = "Ethernet512"
            if hwsku == "Mellanox-SN5610N-C256S2":
                port_alias_to_name_map['etp66'] = "Ethernet520"
        elif hwsku in ["Mellanox-SN5600-C224O8", "Mellanox-SN5610N-C224O8"]:
            split_alias_list = ["a", "b", "c", "d", "e", "f", "g", "h"]
            split_alias_list_1 = ["a", "b"]
            split_2_port_indexs = [13, 17, 45, 49]
            for i in range(1, 65, 2):
                if i in split_2_port_indexs:
                    for idx, split_alias in enumerate(split_alias_list_1):
                        alias = "etp{}{}".format(i, split_alias)
                        eth_name = "Ethernet{}".format((i - 1) * 8 + idx * 4)
                        port_alias_to_name_map[alias] = eth_name
                else:
                    for idx, split_alias in enumerate(split_alias_list):
                        alias = "etp{}{}".format(i, split_alias)
                        eth_name = "Ethernet{}".format((i - 1) * 8 + idx)
                        port_alias_to_name_map[alias] = eth_name
            port_alias_to_name_map['etp65'] = "Ethernet512"
            if hwsku == "Mellanox-SN5610N-C224O8":
                port_alias_to_name_map['etp66'] = "Ethernet520"
        elif hwsku in ["Mellanox-SN5640-C512S2"]:
            split_alias_list = ["a", "b", "c", "d", "e", "f", "g", "h"]
            for i in range(1, 65):
                for idx, split_alias in enumerate(split_alias_list):
                    alias = "etp{}{}".format(i, split_alias)
                    eth_name = "Ethernet{}".format((i - 1) * 8 + idx)
                    port_alias_to_name_map[alias] = eth_name
            port_alias_to_name_map['etp65'] = "Ethernet512"
            port_alias_to_name_map['etp66'] = "Ethernet520"
        elif hwsku in ["Mellanox-SN5640-C448O16"]:
            split_alias_list = ["a", "b", "c", "d", "e", "f", "g", "h"]
            split_alias_list_1 = ["a", "b"]
            split_2_port_indexs = [13, 14, 17, 18, 45, 46, 49, 50]
            for i in range(1, 65):
                if i in split_2_port_indexs:
                    for idx, split_alias in enumerate(split_alias_list_1):
                        alias = "etp{}{}".format(i, split_alias)
                        eth_name = "Ethernet{}".format((i - 1) * 8 + idx * 4)
                        port_alias_to_name_map[alias] = eth_name
                else:
                    for idx, split_alias in enumerate(split_alias_list):
                        alias = "etp{}{}".format(i, split_alias)
                        eth_name = "Ethernet{}".format((i - 1) * 8 + idx)
                        port_alias_to_name_map[alias] = eth_name
            port_alias_to_name_map['etp65'] = "Ethernet512"
            port_alias_to_name_map['etp66'] = "Ethernet520"
        elif hwsku in ["Mellanox-SN4280-O8C80"]:
            idx = 0
            for i in range(1, 13):
                port_alias_to_name_map["etp%da" % i] = "Ethernet%d" % idx
                idx += 2
                port_alias_to_name_map["etp%db" % i] = "Ethernet%d" % idx
                idx += 2
                port_alias_to_name_map["etp%dc" % i] = "Ethernet%d" % idx
                idx += 2
                port_alias_to_name_map["etp%dd" % i] = "Ethernet%d" % idx
                idx += 2
            for i in range(13, 21):
                port_alias_to_name_map["etp%d" % i] = "Ethernet%d" % idx
                idx += 8
            for i in range(21, 29):
                port_alias_to_name_map["etp%da" % i] = "Ethernet%d" % idx
                idx += 2
                port_alias_to_name_map["etp%db" % i] = "Ethernet%d" % idx
                idx += 2
                port_alias_to_name_map["etp%dc" % i] = "Ethernet%d" % idx
                idx += 2
                port_alias_to_name_map["etp%dd" % i] = "Ethernet%d" % idx
                idx += 2
            for i in range(29, 33):
                port_alias_to_name_map["etp%d" % i] = "Ethernet%d" % idx
                idx += 8
        elif hwsku == "ACS-SN4280":
            for i in range(0, 256, 8):
                port_alias_to_name_map["Ethernet%d" % i] = "Ethernet%d" % i
        elif hwsku == "Arista-7060DX5-32":
            for i in range(1, 33):
                port_alias_to_name_map["Ethernet%d/1" % i] = "Ethernet%d" % ((i - 1) * 8)
        elif hwsku == "cisco-8101-p4-32x100-vs":
            # this device simulates 32 ports, with 4 as the step for port naming.
            for i in range(0, 32, 4):
                port_alias_to_name_map["Ethernet%d" % i] = "Ethernet%d" % i
        elif hwsku == "Cisco-8102-28FH-DPU-O-T1":
            for i in range(0, 217, 8):
                port_alias_to_name_map["Ethernet%d" % i] = "Ethernet%d" % i
            for i in range(0, 8, 1):
                port_alias_to_name_map["Ethernet-BP%d" % i] = "Ethernet-BP%d" % i
        elif hwsku == "Nokia-IXR7220-D4-36D":
            for i in range(1, 9):
                port_alias_to_name_map["Ethernet{}/{}".format(i, 1)] = "Ethernet%d" % ((i - 1) * 2)
            for i in range(9, 29):
                port_alias_to_name_map["Ethernet{}/{}".format(i, 1)] = "Ethernet%d" % ((i * 4) - 20)
            for i in range(29, 37):
                port_alias_to_name_map["Ethernet{}/{}".format(i, 1)] = "Ethernet%d" % ((i * 8) - 136)
        elif hwsku == "NH-4010":
            logical_num = 1
            for i in range(0, 505, 8):
                port_alias_to_name_map["Port%d" % logical_num] = "Ethernet%d" % i
                logical_num += 1
            # adding 25G ports
            port_alias_to_name_map["Port65"] = "Ethernet512"
            port_alias_to_name_map["Port66"] = "Ethernet513"

        else:
            if "Arista-7800" in hwsku:
                assert False, "Please add port_alias_to_name_map for new modular SKU %s." % hwsku
            for i in range(0, 128, 4):
                port_alias_to_name_map["Ethernet%d" % i] = "Ethernet%d" % i

    return port_alias_to_name_map, port_alias_asic_map, port_name_to_index_map


def get_port_indices_for_asic(asic_id, port_name_list_sorted):
    front_end_port_name_list = [p for p in port_name_list_sorted if 'BP' not in p and 'IB' not in p and 'Rec' not in p]
    back_end_port_name_list = [p for p in port_name_list_sorted if 'BP' in p or 'IB' in p or 'Rec' in p]
    index_offset = 0
    # Create mapping between port alias and physical index
    port_index_map = {}
    if asic_id:
        index_offset = int(asic_id) * len(front_end_port_name_list)
    for idx, val in enumerate(front_end_port_name_list, index_offset):
        port_index_map[val] = idx
    for idx, val in enumerate(back_end_port_name_list, index_offset):
        port_index_map[val] = idx

    return port_index_map
