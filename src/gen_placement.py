import re
import sys

def generate_placement():
    with open("src/project.v", "r") as f:
        project_v = f.read()
    
    grid_w_match = re.search(r"parameter\s+GRID_W\s*=\s*(\d+);", project_v)
    if not grid_w_match:
        print("Error: Could not find GRID_W parameter in src/project.v")
        sys.exit(1)
    
    grid_w = int(grid_w_match.group(1))
    print(f"Using GRID_W = {grid_w} from src/project.v")

    dffs = []
    
    # We now use the explicit instance names directly from project.v defines!
    for array_type in ["cells", "first_row_cells"]:
        for idx in range(grid_w): # GRID_W parsed from project.v
            d_inst = f"{array_type}_reg[{idx}]" # Yosys naming for behavioral reg array
            delay_inst = f"{array_type}buf_[{idx}]"
            tiehi_inst = f"{array_type}_tie[{idx}]"
            
            dffs.append({
                "inst": d_inst,
                "type": array_type,
                "idx": idx,
                "delay": delay_inst,
                "tiehi": tiehi_inst
            })

    cells_arr = sorted([d for d in dffs if d["type"] == "cells"], key=lambda k: k["idx"])
    first_row_cells_arr = sorted([d for d in dffs if d["type"] == "first_row_cells"], key=lambda k: k["idx"])

    pitch_x = 0.480
    row_height = 3.780
    die_start_x = 2.880
    die_width = 202.080
    die_height = 154.980
    
    # Block sizes in sites
    site_tie = 4
    site_dff = 27
    site_dly = 9
    site_gap = 0 # gap between columns for buffers
    
    site_block = site_dff + site_dly + site_gap
    
    w_block = site_block * pitch_x
    w_dff = site_dff * pitch_x
    w_dly = site_dly * pitch_x

    cells_arr = sorted([d for d in dffs if d["type"] == "cells"], key=lambda k: k["idx"])
    first_row_cells_arr = sorted([d for d in dffs if d["type"] == "first_row_cells"], key=lambda k: k["idx"])

    positions = {} # name -> (x, y, w, h)

    # Configuration for layout limits
    start_row = 1
    block_per_row = 4
    
    with open("src/placement.cfg", "w") as f:
        # Place both groups side by side starting at lower part (row 1)
        # cells: 4 columns on the left (offset 0)
        # first_row_cells: 4 columns on the right
        # We leave a large gap in the middle (approx 40um) for generic logic
        x_offset_group2 = 249 * pitch_x # 119.520 (Snap to right border!)
        for group, x_offset in [(cells_arr, 0), (first_row_cells_arr, x_offset_group2)]:
            for d in group:
                idx = d["idx"]
                r_idx = idx // block_per_row
                
                # Add a skip row (vertical gap) after every 4 placed rows to give routing/buffer space
                skip_offset = r_idx // 4
                r = start_row + r_idx + skip_offset
                
                # Snake order: even rows go left->right, odd rows go right->left
                if r_idx % 2 == 0:
                    c = idx % block_per_row
                else:
                    c = block_per_row - 1 - (idx % block_per_row)
                
                y_pos = 3.780 + (r * row_height)
                orient = "S" if (r % 2 != 0) else "FN"
                
                base_x = die_start_x + x_offset + (c * w_block)
                
                if r_idx % 2 == 0:
                    x_dff = base_x
                    x_dly = x_dff + w_dff
                else:
                    x_dly = base_x
                    x_dff = x_dly + w_dly
                
                f.write(f"{d['inst']} {x_dff:.3f} {y_pos:.3f} {orient}\n")
                positions[d['inst']] = (x_dff, y_pos, w_dff, row_height, "dff_" + d["type"], idx)
                
                if d.get("delay"):
                    f.write(f"{d['delay']} {x_dly:.3f} {y_pos:.3f} {orient}\n")
                    positions[d['delay']] = (x_dly, y_pos, w_dly, row_height, "delay")

    # Draw SVG
    svg_elements = []
    svg_lines = []
    
    def center_of(name):
        if name in positions:
            x, y, w, h, *_ = positions[name]
            return x + w/2, y + h/2
        return None, None

    # Render Rects
    for name, data in positions.items():
        x, y, w, h, t = data[0:5]
        if t == "delay":
            color = "orange"
            label = ""
        elif t.startswith("dff_"):
            color = "blue" if "first_row_cells" not in t else "green"
            idx = data[5]
            label = f"{t.split('_')[1][0]}{idx}"
            
        svg_elements.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{color}" stroke="black" stroke-width="0.2"><title>{name}</title></rect>')
        if label:
            svg_elements.append(f'<text x="{x+w/2}" y="{y+h/2}" font-size="2" fill="white" font-family="sans-serif" text-anchor="middle" dominant-baseline="central" pointer-events="none">{label}</text>')

    # Connect logic correctly based on netlist:
    for d in dffs:
        inst = d["inst"]
        
        # DFF Q to Delay A (local)
        if d.get("delay"):
            x1, y1 = center_of(inst)
            x2, y2 = center_of(d["delay"])
            if x1:
                svg_lines.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="yellow" stroke-width="0.3" pointer-events="none"><title>Q -> A</title></line>')

        # What drives D inputs?
        # Simulate connection based on implicit structural knowledge
        if d["idx"] > 0:
            driver_delay_inst = f"{d['type']}buf_[{d['idx']-1}]"
            x1, y1 = center_of(driver_delay_inst)
            x2, y2 = center_of(inst)
            if x1 and x2:
                svg_lines.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="cyan" stroke-width="0.4" stroke-opacity="0.8" pointer-events="none"><title>{driver_delay_inst} -&gt; DFF</title></line>')

    svg_width = die_width + 80
    svg_header = f'<svg width="{svg_width * 4}" height="{die_height * 4}" viewBox="0 0 {svg_width} {die_height}" xmlns="http://www.w3.org/2000/svg">'
    svg_elements.insert(0, f'<rect x="0" y="0" width="{die_width}" height="{die_height}" fill="none" stroke="red" stroke-width="1"><title>Die Boundaries ({die_width}x{die_height})</title></rect>')
    
    legend = f"""
    <g transform="translate({die_width + 5}, 5)">
      <rect x="0" y="0" width="70" height="35" fill="none" opacity="0.8" stroke="black" stroke-width="0.5"/>
      <rect x="2" y="5" width="5" height="4" fill="blue" stroke="black" stroke-width="0.2"/>
      <text x="9" y="8" font-size="3" font-family="sans-serif">cells DFF</text>
      <rect x="2" y="10" width="5" height="4" fill="green" stroke="black" stroke-width="0.2"/>
      <text x="9" y="13" font-size="3" font-family="sans-serif">first_row_cells DFF</text>
      <rect x="2" y="15" width="5" height="4" fill="orange" stroke="black" stroke-width="0.2"/>
      <text x="9" y="18" font-size="3" font-family="sans-serif">delay (dlygate)</text>
      <line x1="2" y1="23" x2="7" y2="23" stroke="yellow" stroke-width="0.8"/>
      <text x="9" y="24" font-size="3" font-family="sans-serif">DFF -> DELAY</text>
      <line x1="2" y1="28" x2="7" y2="28" stroke="cyan" stroke-opacity="0.8" stroke-width="0.8"/>
      <text x="9" y="29" font-size="3" font-family="sans-serif">DELAY -> Next DFF (Real Nets)</text>
    </g>
    """
    svg_elements.append(legend)
    
    svg_footer = '</svg>'
    
    with open("src/placement.svg", "w") as f:
        f.write(svg_header + "\n")
        f.write("\n".join(svg_elements))
        f.write("\n")
        f.write("\n".join(svg_lines))
        f.write("\n" + svg_footer + "\n")

    print("Success: Generated placement configuration (placement.cfg) and visual mapping (placement.svg).")

if __name__ == "__main__":
    generate_placement()
