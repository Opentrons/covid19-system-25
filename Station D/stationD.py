import math

# metadata
metadata = {
    'protocolName': 'Station D: Sample Transfer',
    'author': 'Chaz <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.3'
}

NUM_SAMPLES = 8
SAMPLE_VOLUME = 5
NUM_SPOTS = 1
NUM_CTRLS = 2
DEST_PLATE = 'bioneer_384_wellplate_20ul'


def run(protocol):

    # load labware
    tips20 = [
        protocol.load_labware(
            'opentrons_96_filtertiprack_20ul',
            s) for s in ['7', '8', '10', '11']]

    p20multi = protocol.load_instrument(
        'p20_multi_gen2', 'left', tip_racks=tips20)
    p20single = protocol.load_instrument(
        'p20_single_gen2', 'right', tip_racks=tips20)

    tempDeck = protocol.load_module('temperature module gen2', '1')
    tempPlate = tempDeck.load_labware(
        'opentrons_96_aluminumblock_nest_wellplate_100ul')
    num_cols = math.ceil(NUM_SAMPLES/8)
    sampWells = [
        w for w in tempPlate.rows()[0][:num_cols] for _ in range(NUM_SPOTS)]

    controls = protocol.load_labware(
        'opentrons_24_aluminumblock_nest_1.5ml_snapcap', '3')

    destPlate = protocol.load_labware(DEST_PLATE, '2')
    if len(destPlate.wells()) > 96:
        destWells = [well for row in destPlate.rows()[:2] for well in row]
    else:
        destWells = destPlate.row()[0]

    tempDeck.set_temperature(4)

    # transfer samples
    for src, dest in zip(sampWells, destWells):
        p20multi.pick_up_tip()
        p20multi.mix(3, SAMPLE_VOLUME, src)
        p20multi.aspirate(SAMPLE_VOLUME, src)
        p20multi.dispense(SAMPLE_VOLUME, dest)
        p20multi.mix(3, SAMPLE_VOLUME, dest)
        p20multi.blow_out()
        p20multi.drop_tip()

    # transfer controls
    if NUM_CTRLS > 0:
        n_ctrls = NUM_CTRLS * -1
        ctrl_wells = controls.wells()[:NUM_CTRLS]
        if len(destPlate.wells()) > 96:
            dest_wells = destPlate.rows()[-1][n_ctrls:]
        else:
            dest_wells = destPlate.wells()[n_ctrls:]
        for src, dest in zip(ctrl_wells, dest_wells):
            p20single.pick_up_tip()
            p20single.mix(3, SAMPLE_VOLUME, src)
            p20single.aspirate(SAMPLE_VOLUME, src)
            p20single.dispense(SAMPLE_VOLUME, dest)
            p20single.mix(3, SAMPLE_VOLUME, dest)
            p20single.blow_out()
            p20single.drop_tip()
