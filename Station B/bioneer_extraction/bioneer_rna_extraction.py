from opentrons import types
import math

metadata = {
    'protocolName': 'Bioneer RNA Extraction',
    'author': 'Chaz <chaz@opentrons.com>',
    'apiLevel': '2.7'
}

NUM_SAMPLES = 96  # the number of samples to run
NUM_COLS = math.ceil(NUM_SAMPLES/8)


def run(protocol):
    # load labware
    magdeck = protocol.load_module('magnetic module', '7')
    magplate = magdeck.load_labware('nest_96_wellplate_2ml_deep')
    waste1 = protocol.load_labware(
        'nest_1_reservoir_195ml', '10').wells()[0].top()
    waste2 = protocol.load_labware(
        'nest_1_reservoir_195ml', '11').wells()[0].top()
    res1 = protocol.load_labware('nest_12_reservoir_15ml', '8')
    res2 = protocol.load_labware('nest_1_reservoir_195ml', '9')
    res3 = protocol.load_labware('nest_12_reservoir_15ml', '6')
    pcrplate = protocol.load_labware('nest_96_wellplate_100ul_pcr_full_skirt', '3')

    tips200 = [
        protocol.load_labware(
            'opentrons_96_tiprack_300ul', s, 'P300-Multi Tips') for s in ['5', '4', '2', '1']
        ]
    all_tips = [tr['A'+str(i)] for tr in tips200 for i in range(1, 13)]
    tips1, tips2, tips3, tips4 = [
        all_tips[i*12:(i+1)*12] for i in range(4)]

    m300 = protocol.load_instrument('p300_multi_gen2', 'left')

    # create reagent locations as variables
    vb = [res1[x] for x in ['A1', 'A2'] for _ in range(6)][:NUM_COLS]
    etoh = [res1[x] for x in ['A4', 'A5', 'A6'] for _ in range(4)][:NUM_COLS]
    magbeads = [res1[x] for x in ['A8', 'A9'] for _ in range(6)][:NUM_COLS]
    vwm1 = [res2['A1']]*NUM_COLS
    rwa2 = [res3['A'+str(x)] for x in range(1, 7) for _ in range(2)][:NUM_COLS]
    we = [res3['A'+str(x)] for x in range(7, 13) for _ in range(2)][:NUM_COLS]
    er = [res1['A12']]*NUM_COLS

    magheight = 13.7

    magsamps, elutes = [p.rows()[0][:NUM_COLS] for p in [magplate, pcrplate]]

    m300.flow_rate.aspirate = 50
    m300.flow_rate.dispense = 150
    m300.flow_rate.blow_out = 300

    def well_mix(reps, loc, v, side):
        loc1 = loc.bottom().move(types.Point(x=side, y=0, z=3))
        loc2 = loc.bottom().move(types.Point(x=side*-1, y=0, z=0.6))
        m300.aspirate(20, loc1)
        mvol = v-20
        for _ in range(reps-1):
            m300.aspirate(mvol, loc1)
            m300.dispense(mvol, loc2)
        m300.dispense(20, loc2)

    def remove_supernatant(vol, src, dest, side):
        m300.flow_rate.aspirate = 20
        m300.aspirate(10, src.top())
        while vol > 180:
            m300.aspirate(
                180, src.bottom().move(types.Point(x=side, y=0, z=0.5)))
            m300.dispense(190, dest)
            m300.aspirate(10, dest)
            vol -= 180
        m300.aspirate(vol, src.bottom().move(types.Point(x=side, y=0, z=0.5)))
        m300.dispense(vol, dest)
        m300.dispense(10, dest)
        m300.flow_rate.aspirate = 50

    def add_reagent(reagent, vol, tips, retips, return_tips=True):
        """This function is used for adding reagents"""
        for well, t, ret, s, re in zip(magsamps, tips, retips, sides, reagent):
            m300.pick_up_tip(t)
            add_vol = vol
            e_vol = 0
            while add_vol > 200:
                m300.aspirate(200, re)
                m300.dispense(200, well.top(-3))
                m300.aspirate(10, well.top(-3))
                add_vol -= 200
                e_vol += 10
            m300.aspirate(add_vol, re)
            total_vol = add_vol + e_vol
            m300.dispense(total_vol, well)

            well_mix(10, well, 180, s)

            m300.blow_out()

            if return_tips:
                m300.drop_tip(ret)
            else:
                m300.drop_tip()

    sides = [-1, 1]*6

    # Add 200uL of VB Buffer to each well and mix
    protocol.comment('Adding 200uL of VB Buffer to each well...')
    add_reagent(vb, 200, tips1, tips1, return_tips=False)

    protocol.pause('Please remove the plate for incubation...')

    # add 400uL of ethanol
    protocol.comment('Adding 400uL of ethanol to each well...')
    add_reagent(etoh, 400, tips2, tips1, return_tips=False)

    # add 200uL of magbeads
    protocol.comment('Adding 200uL of MagBeads to each well...')
    add_reagent(magbeads, 200, tips3, tips2)

    protocol.comment('Engaging MagDeck...')
    magdeck.engage(height=magheight)
    protocol.delay(minutes=3)

    protocol.comment('Removing supernatant...')
    for well, tip, rtip, s in zip(magsamps, tips2, tips1, sides):
        m300.pick_up_tip(tip)
        remove_supernatant(1010, well, waste1, s)
        m300.drop_tip(rtip)

    # First Wash: Add 700uL of VWM1 Buffer
    protocol.comment('First Wash: Adding 700uL of VWM1 Buffer...')
    add_reagent(vwm1, 700, tips4, tips3)

    protocol.comment('Engaging MagDeck...')
    magdeck.engage(height=magheight)
    protocol.delay(minutes=3)

    protocol.comment('Removing supernatant...')
    for idx, (well, tip, rtip, s) in enumerate(zip(magsamps, tips3, tips2, sides)):
        w = waste1 if idx < 6 else waste2
        m300.pick_up_tip(tip)
        remove_supernatant(700, well, w, s)
        m300.drop_tip(rtip)

    magdeck.disengage()

    # replace tips before continuing
    protocol.pause('Please empty trash bin and replace all tips. When ready, click RESUME')

    # Second Wash: Add 700uL of VWM1 Buffer
    protocol.comment('Second Wash: Adding 700uL of VWM1 Buffer...')
    add_reagent(vwm1, 700, tips4, tips4, return_tips=False)

    protocol.comment('Engaging MagDeck...')
    magdeck.engage(height=magheight)
    protocol.delay(minutes=3)

    protocol.comment('Removing supernatant...')
    for idx, (well, tip, s) in enumerate(zip(magsamps, tips3, sides)):
        m300.pick_up_tip(tip)
        remove_supernatant(700, well, waste2, s)
        m300.drop_tip()

    magdeck.disengage()

    # Third Wash: Add 700uL of RWA2 Buffer
    protocol.comment('Third Wash: Adding 700uL of RWA2 Buffer...')
    add_reagent(rwa2, 700, tips2, tips3)

    protocol.comment('Engaging MagDeck...')
    magdeck.engage(height=magheight)
    protocol.delay(minutes=3)

    protocol.comment('Removing supernatant...')
    for well, tip, rtip, s in zip(magsamps, tips3, tips4, sides):
        m300.pick_up_tip(tip)
        remove_supernatant(700, well, waste2, s)
        m300.drop_tip(rtip)

    # Fourth Wash: Add 700uL of WE Buffer
    protocol.comment('Fourth Wash: Adding 700uL of WE Buffer...')
    add_reagent(we, 700, tips1, tips2)

    protocol.comment('Removing supernatant...')
    for well, tip, rtip, s in zip(magsamps, tips2, tips3, sides):
        m300.pick_up_tip(tip)
        remove_supernatant(700, well, waste2, s)
        m300.drop_tip(rtip)

    magdeck.disengage()

    # replace tips before continuing
    protocol.pause('Please replace USED TIPS (only). When ready, click RESUME')

    # Add 100uL of ER Buffer for elution
    protocol.comment('Fourth Wash: Adding 100uL of ER Buffer...')
    add_reagent(er, 100, tips4, tips2)

    protocol.pause('Incubate at 60C for 1 minute...')

    protocol.comment('Transferring elution to PCR Plate...')
    m300.flow_rate.aspirate = 20
    for src, dest, t1, t2, s in zip(magsamps, elutes, tips3, tips1, sides):
        m300.pick_up_tip(t1)
        m300.aspirate(
            100, src.bottom().move(types.Point(x=s, y=0, z=0.5)))
        m300.dispense(100, dest)
        m300.blow_out()
        m300.drop_tip(t2)

    protocol.comment('Protocol complete!')
