import odb
import json
import os

steps = [
    ("Floorplan", "src/runs/precise_place/13-openroad-floorplan/tt_um_vga_ca.odb"),
    ("Global Place", "src/runs/precise_place/28-openroad-globalplacement/tt_um_vga_ca.odb"),
    ("Detailed Place", "src/runs/precise_place/34-openroad-detailedplacement/tt_um_vga_ca.odb"),
    ("CTS", "src/runs/precise_place/35-openroad-cts/tt_um_vga_ca.odb"),
    ("Detailed Route", "src/runs/precise_place/44-openroad-detailedrouting/tt_um_vga_ca.odb"),
    ("Final", "src/runs/precise_place/final/odb/tt_um_vga_ca.odb"),
]

data = {"steps": []}

for label, path in steps:
    if not os.path.exists(path):
        continue
    print(f"Processing {label}...")
    db = odb.dbDatabase.create()
    try:
        odb.read_db(db, path)
        chip = db.getChip()
        block = chip.getBlock()
        die_area = block.getDieArea()
        
        step_data = {
            "label": label,
            "die_area": [die_area.xMin(), die_area.yMin(), die_area.xMax(), die_area.yMax()],
            "instances": [],
            "nets": []
        }
        
        # Standard Instances
        for inst in block.getInsts():
            master = inst.getMaster()
            bbox = inst.getBBox()
            pins = {}
            for iterm in inst.getITerms():
                res = iterm.getAvgXY()
                if isinstance(res, (list, tuple)) and res[0]:
                    pins[iterm.getMTerm().getName()] = [res[1], res[2]]

            step_data["instances"].append({
                "name": inst.getName(),
                "type": master.getName(),
                "bbox": [bbox.xMin(), bbox.yMin(), bbox.xMax(), bbox.yMax()],
                "pins": pins
            })
        
        # IO Pins
        for bterm in block.getBTerms():
            name = "PIN:" + bterm.getName()
            res = bterm.getFirstPinLocation()
            pos = [res[1], res[2]] if (isinstance(res, (list, tuple)) and res[0]) else [0, 0]
            step_data["instances"].append({
                "name": name,
                "type": "IO_PIN",
                "bbox": [pos[0]-500, pos[1]-500, pos[0]+500, pos[1]+500],
                "pins": {"P": pos}
            })

        # Nets
        for net in block.getNets():
            if net.getSigType() in ["POWER", "GROUND"]: continue
            
            conns = []
            for iterm in net.getITerms():
                conns.append({
                    "inst": iterm.getInst().getName(),
                    "pin": iterm.getMTerm().getName(),
                    "is_drv": "OUTPUT" in str(iterm.getIoType())
                })
            for bterm in net.getBTerms():
                conns.append({
                    "inst": "PIN:" + bterm.getName(),
                    "pin": "P",
                    "is_drv": "INPUT" in str(bterm.getIoType())
                })
            
            wire_segments = []
            wire = net.getWire()
            if wire:
                decoder = odb.dbWireDecoder()
                decoder.begin(wire)
                last_pt = None
                while True:
                    op = decoder.next()
                    if op == odb.dbWireDecoder.END_DECODE: break
                    
                    if op == odb.dbWireDecoder.PATH: 
                        last_pt = None
                    elif op in [odb.dbWireDecoder.JUNCTION, odb.dbWireDecoder.POINT]:
                        curr_pt = decoder.getPoint()
                        if last_pt:
                            wire_segments.append([last_pt[0], last_pt[1], curr_pt[0], curr_pt[1]])
                        last_pt = curr_pt
                    elif op in [odb.dbWireDecoder.VIA, odb.dbWireDecoder.TECH_VIA]:
                        last_pt = decoder.getPoint()

            if len(conns) > 1 or wire_segments:
                step_data["nets"].append({
                    "name": net.getName(),
                    "conns": conns,
                    "wires": wire_segments
                })
                
        data["steps"].append(step_data)
    finally:
        odb.dbDatabase.destroy(db)

with open("layout_data.json", "w") as f:
    json.dump(data, f)
