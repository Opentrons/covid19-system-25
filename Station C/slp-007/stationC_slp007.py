import csv
import os

# metadata
metadata = {
    'protocolName': 'Station C SLP-007',
    'author': 'Chaz <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.3'
}

TIP_TRACK = False
RACK_DEF = 'opentrons_24_tuberack_generic_2ml_screwcap'
PIP_CTRL = False


def run(protocol):

    # load labware
    m20tips = protocol.load_labware('opentrons_96_filtertiprack_20ul', '7')
    m20 = protocol.load_instrument('p20_multi_gen2', 'left')
    ctrl_blk = protocol.load_labware('opentrons_96_aluminumblock_generic_pcr_strip_200ul', '4')
    plate384 = protocol.load_labware('bioneer_384_wellplate_20ul', '1')

    # only used if adding controls with single channel
    s300tips = protocol.load_labware('opentrons_96_filtertiprack_20ul', '10')
    s300 = protocol.load_instrument('p20_single_gen2', 'right')
    ctrl_rack = protocol.load_labware(RACK_DEF, '3')

    # Tip tracking between runs
    if TIP_TRACK and not protocol.is_simulating():
        file_path = '/data/csv/tiptracking.csv'
        file_dir = os.path.dirname(file_path)
        # check for file directory
        if not os.path.exists(file_dir):
            os.makedirs(file_dir)
        # check for file; if not there, create initial tip count tracking
        if not os.path.isfile(file_path):
            with open(file_path, 'w') as outfile:
                outfile.write("0, 0\n")

    tip_count_list = []
    if not TIP_TRACK or protocol.is_simulating():
        tip_count_list = [0, 0]
    else:
        with open(file_path) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            tip_count_list = next(csv_reader)

    m20count = int(tip_count_list[0])
    s300count = int(tip_count_list[1])

    def pick_up(pip):
        nonlocal m20count
        nonlocal s300count

        if pip == m20:
            if m20count == 12:
                protocol.pause('Please replace tips in slot 7 for multi')
            m20.pick_up_tip(m20tips.rows()[0][m20count])
            m20count += 1
        else:
            if s300count == 96:
                protocol.pause('Replace tips in slot 10 for single channel pipette.')
            s300.pick_up_tip(s300tips.wells()[s300count])
            s300count += 1

    if PIP_CTRL:
        n1 = ctrl_rack['A1']
        n2 = ctrl_rack['B1']
        n1c = [well for col in ctrl_blk.columns()[:2] for well in col]
        n2c = [well for col in ctrl_blk.columns()[10:] for well in col]

        for src, dest in zip([n1, n2], [n1c, n2c]):
            pick_up(s300)
            for well in dest:
                s300.aspirate(35, src)
                s300.dispense(35, well)
            s300.drop_tip()

    src_tubes = [ctrl_blk[x] for x in ['A1', 'A2', 'A11', 'A12']]
    dest_wells = [
        plate384.rows()[0][:12],
        plate384.rows()[0][12:],
        plate384.rows()[1][:12],
        plate384.rows()[1][12:]
        ]

    m20vol = 0
    for src, dest in zip(src_tubes, dest_wells):
        pick_up(m20)
        for well in dest:
            if m20vol < 4:
                m20.dispense(m20vol, src)
                m20.aspirate(15, src)
                m20vol = 15
            m20.dispense(2.1, well)
            m20vol -= 2.1
        m20.dispense(m20vol, src)
        m20vol = 0
        m20.drop_tip()
