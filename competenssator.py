import math
import os
import re
import random
import shutil
from datetime import datetime
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF

import networkx as nx
import svgwrite
import yaml

backgroundColor = "rgb(255,255,255)"
lightColor = "rgb(230,230,230)"
darkColor = "rgb(10,10,10)"

polkaUrl = ""
polka2Url = ""
gradientUrl = ""

# Section colours (colourful, no B&W)
SECTION_COLORS = [
    ("black", "aquamarine"),
    ("black", "lightblue"),
    ("black", "lightgreen"),
    ("black", "tomato"),
    ("black", "lightyellow"),
    ("black", "lightpink"),
    ("black", "lightgrey"),
    ("black", "peachpuff"),
    ("black", "paleturquoise"),
    ("black", "lavender"),
]

# State stroke colours used on top of section fills
STATE_STROKES = {
    'locked':         '#999999',
    'available':      None,          # inherits section stroke
    'claimed':        '#b8860b',
    'validated':      '#2E7D32',
    'rejected':       '#c62828',
    # teacher group-stats states
    'all_validated':  '#2E7D32',
    'some_validated': '#388E3C',
    'pending':        '#b8860b',
    'not_started':    None,          # inherits section stroke
}


class Style:
    def __init__(self, strokeColor, fillColor, fillUrl=""):
        self.strokeColor = strokeColor
        self.fillColor = fillColor
        self.fillUrl = fillUrl
        self.stroke_dasharray = 1
        self.number_of_strokes = 1


class Config:
    def __init__(self, blackAndWhite, withTickBox):
        self.blackAndWhite = blackAndWhite
        self.withTickBox = withTickBox


class HexGrid:
    def __init__(self, size, rowCount, colCount):
        self.size = size
        self.rowCount = rowCount
        self.colCount = colCount

    def rowFor(self, index):
        return index // self.colCount

    def colFor(self, index):
        return index % self.colCount

    def rowAndColFor(self, index):
        return (self.rowFor(index), self.colFor(index))

    def yFor(self, rowA):
        return self.size * (0.5 + rowA * math.sqrt(3) + math.sqrt(3) / 2)

    def xFor(self, colA, rowA):
        return self.size * (2 * colA + (0 if rowA % 2 == 0 else 1) + 1)

    def areIndexConnected(self, indexA, indexB):
        indexA, indexB = (min(indexA, indexB), max(indexA, indexB))
        rowA, colA = (self.rowFor(indexA), self.colFor(indexA))
        rowB, colB = (self.rowFor(indexB), self.colFor(indexB))
        diffRow = abs(rowA - rowB)
        diffCol = abs(colA - colB)
        if diffRow == 0:
            return diffCol == 1
        elif diffRow > 1:
            return False
        elif diffRow == 1:
            if diffCol == 0:
                return True
            elif rowA % 2 == 0:
                return colA - colB == 1
            elif rowA % 2 == 1:
                return colB - colA == 1
        return False

    def distance(self, indexA, indexB):
        if self.areIndexConnected(indexA, indexB):
            return 0
        indexA, indexB = (min(indexA, indexB), max(indexA, indexB))
        rowA, colA = (self.rowFor(indexA), self.colFor(indexA))
        rowB, colB = (self.rowFor(indexB), self.colFor(indexB))
        return abs(rowA - rowB) + abs(colA - colB) + 1

    @staticmethod
    def bestCount(size):
        tailles = [(2, 3), (3, 4), (4, 5), (5, 6), (6, 8), (7, 10), (8, 11), (9, 12)]
        for (row, col) in tailles:
            if row * col >= size:
                return (row, col)
        cols = math.ceil(math.sqrt(size * 1.5))
        rows = math.ceil(size / cols)
        return (rows, cols)


def split_string_by_length(text, max_length):
    words = text.split()
    segments = []
    current_segment = ''
    for word in words:
        if len(current_segment) + len(word) <= max_length:
            current_segment += ' ' + word if current_segment else word
        else:
            segments.append(current_segment)
            current_segment = word
    if current_segment:
        segments.append(current_segment)
    return segments


def section_style_for(element, parts):
    """Return a Style using colourful section colours (no B&W, no tickbox)."""
    idx = find_part_containing(element, parts)
    stroke, fill = SECTION_COLORS[idx % len(SECTION_COLORS)]
    return Style(stroke, fill)


def styles(config):
    """Legacy style list (used by old yaml_to_svgs path)."""
    colors = ["aquamarine", "lightblue", "lightgreen", "tomato",
              "lightyellow", "lightpink", "lightgrey"]
    result = []
    for color in colors:
        s = Style("black", color)
        result.append(s)
    return result


def styleFor(element, parts, config):
    return section_style_for(element, parts)


def draw_hexagon(dwg, center_x, center_y, grid, text, style, config,
                 container=None, annotation=None):
    if text == "___":
        return
    if container is None:
        container = dwg
    stroke_width = 3
    number_of_strokes = style.number_of_strokes
    perimeters = [1.0, .85, .7][:number_of_strokes]
    xBox, yBox = (0, 0)
    for perimeter in perimeters:
        path = ""
        roundPercent = 0.15
        points = []
        for i in range(6):
            angle_rad = math.radians(30 + 60 * i)
            x = center_x + grid.size * math.cos(angle_rad) * perimeter
            y = center_y + grid.size * math.sin(angle_rad) * perimeter
            if i == 0 and perimeter == 1.0:
                xBox = center_x + grid.size * .8 * math.cos(angle_rad)
                yBox = center_y + grid.size * .8 * math.sin(angle_rad)
            points.append((x, y))
        for i in range(6):
            x1, y1 = points[i]
            x2, y2 = points[(i + 1) % 6]
            x3, y3 = points[(i + 2) % 6]
            x21 = roundPercent * x1 + (1 - roundPercent) * x2
            y21 = roundPercent * y1 + (1 - roundPercent) * y2
            x23 = (1 - roundPercent) * x2 + roundPercent * x3
            y23 = (1 - roundPercent) * y2 + roundPercent * y3
            if path == "":
                path += "M " + str(x21) + "," + str(y21)
            else:
                path += " L " + str(x21) + "," + str(y21)
            path += " Q " + str(x2) + "," + str(y2) + " " + str(x23) + "," + str(y23)
        path += " Z"
        extra = {}
        if style.stroke_dasharray != 1:
            extra['stroke_dasharray'] = (str(style.stroke_dasharray) + ","
                                         + str(style.stroke_dasharray))
        container.add(dwg.path(
            d=path,
            fill=style.fillColor if style.fillUrl == "" else style.fillUrl,
            stroke=style.strokeColor,
            stroke_width=stroke_width / number_of_strokes,
            stroke_linecap="round",
            **extra))
    draw_text_multiline(center_x, center_y, dwg, grid, style, text,
                        container=container, annotation=annotation)


def draw_text_multiline(center_x, center_y, dwg, grid, style, text,
                        container=None, annotation=None):
    if container is None:
        container = dwg
    lines = split_string_by_length(text, 13)
    fill = "#000"
    stroke = "#fff"
    base = ("font-family:Arial;font-weight:700;"
            "font-size:{};text-anchor:middle;".format(grid.size * 0.17))
    styleSVG = base + "stroke-width:{};stroke:{};fill:{};".format(
        grid.size * 0.007, fill, fill)
    style2SVG = base + "stroke-width:{};stroke:{};fill:{};".format(
        grid.size * 0.04, stroke, stroke)
    for i, line in enumerate(lines):
        lineheight = grid.size / 4
        y = center_y - grid.size / 3 + lineheight * i
        tr = "rotate(-30, {}, {})".format(center_x, center_y)
        container.add(dwg.text(line, insert=(center_x, y), style=style2SVG, transform=tr))
        container.add(dwg.text(line, insert=(center_x, y), style=styleSVG, transform=tr))

    if annotation:
        ann_size = grid.size * 0.14
        ann_base = ("font-family:Arial;font-weight:600;"
                    "font-size:{};text-anchor:middle;".format(ann_size))
        tr = "rotate(-30, {}, {})".format(center_x, center_y)
        y_ann = center_y + grid.size * 0.40
        container.add(dwg.text(annotation, insert=(center_x, y_ann),
                                style=ann_base + "stroke-width:0.03em;stroke:#fff;fill:#fff;",
                                transform=tr))
        container.add(dwg.text(annotation, insert=(center_x, y_ann),
                                style=ann_base + "stroke-width:0;fill:#222;",
                                transform=tr))


def find_part_containing(element, parts):
    for i, part in enumerate(parts):
        if element in part:
            return i
    return 0


# ---------------------------------------------------------------------------
# Placement evaluation
# ---------------------------------------------------------------------------

def evaluation(individual, G, grid):
    asList = list(individual)
    score = 0.0
    center_row = (grid.rowCount - 1) / 2.0
    center_col = (grid.colCount - 1) / 2.0

    for (a, b) in G.edges:
        ia = asList.index(a)
        ib = asList.index(b)
        if grid.areIndexConnected(ia, ib):
            score += 40.0
        else:
            d = grid.distance(ia, ib)
            score -= d * d * 12.0

    for node in G.nodes:
        idx = asList.index(node)
        row, col = grid.rowAndColFor(idx)
        degree = G.degree(node)
        if degree > 1:
            dist_c = math.sqrt((row - center_row) ** 2 + (col - center_col) ** 2)
            score -= degree * dist_c * 2.0

    for source in [s for s in G.nodes if G.in_degree(s) == 0]:
        score -= grid.rowFor(asList.index(source)) * 3.0

    return score


def hill_climb(strings, G, grid, eval_fn, seed):
    random.seed(seed)
    current = strings[:]
    random.shuffle(current)
    current_score = eval_fn(current, G, grid)
    improved = True
    while improved:
        improved = False
        n = len(current)
        for a in range(n):
            for b in range(a + 1, n):
                candidate = current[:]
                candidate[a], candidate[b] = candidate[b], candidate[a]
                s = eval_fn(candidate, G, grid)
                if s > current_score:
                    current_score = s
                    current = candidate
                    improved = True
                    break
            if improved:
                break
    return current_score, current


def _grid_variants(n_skills: int) -> list:
    base_r, base_c = HexGrid.bestCount(n_skills)
    seen = {(base_r, base_c)}
    variants = [(base_r, base_c)]
    for extra in range(1, max(n_skills, 2)):
        c = base_c + extra
        r = math.ceil(n_skills / c)
        if r < base_r and r >= 2 and (r, c) not in seen:
            seen.add((r, c))
            variants.append((r, c))
            break
    for extra in range(1, max(n_skills, 2)):
        r = base_r + extra
        c = math.ceil(n_skills / r)
        if c < base_c and c >= 2 and (r, c) not in seen:
            seen.add((r, c))
            variants.append((r, c))
            break
    return variants[:3]


def _ensure_results_folder():
    os.makedirs(os.path.join(".", "results"), exist_ok=True)


def compute_layout_options(data, n_seeds: int = 3) -> list:
    G = get_graph_from_data(data)
    strings = list(G.nodes)
    config = read_config_from_yaml(data)
    variants = _grid_variants(len(strings))
    _ensure_results_folder()
    labels = ['Compact', 'Large', 'Vertical']
    options = []
    seed_base = 1
    for i, (rows, cols) in enumerate(variants):
        padded = strings + ['___'] * (rows * cols - len(strings))
        grid = HexGrid(50, rows, cols)
        best_score, best_order = None, None
        for s in range(seed_base, seed_base + n_seeds):
            score, order = hill_climb(padded, G, grid, evaluation, s)
            if best_score is None or score > best_score:
                best_score = score
                best_order = order
        seed_base += n_seeds
        svg = draw_skill_tree(best_order, G, grid, config, generate_pdf=False)
        options.append({
            'order': best_order,
            'rows': rows,
            'cols': cols,
            'score': best_score,
            'label': labels[i] if i < len(labels) else 'Option {}'.format(i + 1),
            'svg': svg,
        })
    return options


def compute_best_order(data) -> dict:
    G = get_graph_from_data(data)
    strings = list(G.nodes)
    rows, cols = HexGrid.bestCount(len(strings))
    padded = strings + ['___'] * (rows * cols - len(strings))
    grid = HexGrid(50, rows, cols)
    _ensure_results_folder()
    _, best = hill_climb(padded, G, grid, evaluation, 1)
    return {'order': best, 'rows': rows, 'cols': cols}


def draw_with_states(data, layout: dict, skill_states=None) -> str:
    """Draw SVG from a layout dict: {'order': [...], 'rows': int, 'cols': int}."""
    config = read_config_from_yaml(data)
    G = get_graph_from_data(data)
    order = layout['order']
    rows = layout.get('rows')
    cols = layout.get('cols')
    if rows is None or cols is None:
        real = [s for s in order if s != '___']
        rows, cols = HexGrid.bestCount(len(real))
    grid = HexGrid(50, rows, cols)
    return draw_skill_tree(order, G, grid, config,
                           skill_states=skill_states, generate_pdf=False)


def draw_with_group_stats(data, layout: dict, skill_stats: dict,
                          total_students: int) -> str:
    """Draw SVG for teacher group view with per-skill validation statistics.

    skill_stats: {skill_name: {'validated': int, 'claimed': int}}
    total_students: total enrolled students
    """
    config = read_config_from_yaml(data)
    G = get_graph_from_data(data)
    order = layout['order']
    rows = layout.get('rows')
    cols = layout.get('cols')
    if rows is None or cols is None:
        real = [s for s in order if s != '___']
        rows, cols = HexGrid.bestCount(len(real))
    grid = HexGrid(50, rows, cols)

    skill_states = {}
    annotations = {}
    for skill in G.nodes:
        stats = skill_stats.get(skill, {})
        validated = stats.get('validated', 0)
        claimed = stats.get('claimed', 0)
        if total_students > 0 and validated >= total_students:
            skill_states[skill] = 'all_validated'
        elif validated > 0:
            skill_states[skill] = 'some_validated'
        elif claimed > 0:
            skill_states[skill] = 'pending'
        else:
            skill_states[skill] = 'not_started'
        if total_students > 0:
            ann = '\u2713{}/{}'.format(validated, total_students)
            if claimed > 0:
                ann += ' \u23f3{}'.format(claimed)
            annotations[skill] = ann
        else:
            annotations[skill] = ''

    return draw_skill_tree(order, G, grid, config,
                           skill_states=skill_states,
                           annotations=annotations,
                           generate_pdf=False)


# ---------------------------------------------------------------------------
# SVG drawing
# ---------------------------------------------------------------------------

def draw_skill_tree(skills, G, grid, config, skill_states=None,
                    annotations=None, generate_pdf=True):
    global polkaUrl, polka2Url, gradientUrl
    width = grid.size * (2 * grid.colCount + 1)
    height = grid.size * (2 * grid.rowCount + 0.5)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    file_name = "results/" + timestamp + ".svg"

    dwg = svgwrite.Drawing(
        filename=file_name if generate_pdf else '',
        profile='full',
        size=(str(width), str(height)))
    dwg.viewbox(0, 0, width, height)

    radial = dwg.defs.add(dwg.radialGradient((0.5, 0.5), r=.6, fx=0.5, fy=0.5))
    radial.add_stop_color(offset='0%', color='#000')
    radial.add_stop_color(offset='100%', color='#fff')

    polka = dwg.defs.add(dwg.pattern(id="polka", size=(10, 10),
                                     patternUnits="userSpaceOnUse",
                                     patternTransform="rotate(30)"))
    polka.add(dwg.circle(center=(5, 5), r=1, fill='#999'))
    polkaUrl = polka.get_funciri()

    polka2 = dwg.defs.add(dwg.pattern(id="polka2", size=(2, 8),
                                      patternUnits="userSpaceOnUse",
                                      patternTransform="rotate(150)"))
    polka2.add(dwg.circle(center=(1, 1), r=.5, fill='#666'))
    polka2Url = polka2.get_funciri()

    gradientUrl = radial.get_funciri()
    dwg.add(dwg.rect(insert=(0, 0), size=('100%', '100%'), rx=None, ry=None, fill="white"))

    parts = list(nx.connected_components(G.to_undirected()))
    hex_attr_map = {}

    for element in skills:
        index = skills.index(element)
        (row, col) = grid.rowAndColFor(index)
        x = grid.size * (2 * col + (0 if row % 2 == 0 else 1) + 1)
        y = grid.size * (0.5 + row * math.sqrt(3) + math.sqrt(3) / 2)
        ann = annotations.get(element) if annotations else None

        if skill_states is not None and element != '___':
            state = skill_states.get(element, 'locked')
            sec = section_style_for(element, parts)

            # Section fill preserved for all non-locked states;
            # stroke colour encodes the state.
            if state == 'locked':
                style = Style('#aaaaaa', '#e0e0e0')
            elif state == 'available':
                style = Style(sec.strokeColor, sec.fillColor)
            elif state == 'claimed':
                style = Style('#b8860b', sec.fillColor)
                style.number_of_strokes = 2
            elif state == 'validated':
                style = Style('#2E7D32', sec.fillColor)
            elif state == 'rejected':
                style = Style('#c62828', sec.fillColor)
            elif state == 'all_validated':
                style = Style('#1B5E20', '#a5d6a7')
            elif state == 'some_validated':
                style = Style('#388E3C', sec.fillColor)
            elif state == 'pending':
                style = Style('#b8860b', sec.fillColor)
            else:  # not_started
                style = sec

            skill_id = re.sub(r'[^a-zA-Z0-9]', '_', element)
            g_elem = dwg.g(id='hex-' + skill_id)
            hex_attr_map[skill_id] = (element, state)
            draw_hexagon(dwg, x, y, grid, element, style, config,
                         container=g_elem, annotation=ann)
            dwg.add(g_elem)
        else:
            style = section_style_for(element, parts)
            draw_hexagon(dwg, x, y, grid, element, style, config, annotation=ann)

    marker = dwg.defs.add(dwg.marker(insert=(1, 1), size=(2, 2), orient='auto',
                                     markerUnits='strokeWidth', id='arrowhead'))
    marker.add(dwg.path(d='M0,0 L0,2 L2,1 z', fill='black'))
    marker2 = dwg.defs.add(dwg.marker(insert=(1, 1), size=(2, 2), orient='auto',
                                      markerUnits='strokeWidth', id='arrowhead2'))
    marker2.add(dwg.path(d='M0,0 L0,2 L2,1 z', fill='white'))

    for (a, b) in G.edges:
        indexA = skills.index(a)
        indexB = skills.index(b)
        rowA, colA = grid.rowAndColFor(indexA)
        rowB, colB = grid.rowAndColFor(indexB)
        x1 = grid.xFor(colA, rowA)
        y1 = grid.yFor(rowA)
        x2 = grid.xFor(colB, rowB)
        y2 = grid.yFor(rowB)
        xStart = x1 + (x2 - x1) * 2 / 5
        yStart = y1 + (y2 - y1) * 2 / 5
        xEnd = x1 + (x2 - x1) * 3 / 5
        yEnd = y1 + (y2 - y1) * 3 / 5
        dwg.add(dwg.line(start=(xStart, yStart), end=(xEnd, yEnd),
                         stroke="black", stroke_width=5, stroke_linecap='round',
                         marker_end=marker.get_funciri()))
        dwg.add(dwg.line(start=(xStart, yStart), end=(xEnd, yEnd),
                         stroke="white", stroke_width=3, stroke_linecap='round',
                         marker_end=marker2.get_funciri()))

    if generate_pdf:
        dwg.save()
        try:
            drawing = svg2rlg(file_name)
            renderPDF.drawToFile(drawing, "./results/file.pdf")
        except Exception:
            pass

    svg_str = dwg.tostring()
    if hex_attr_map:
        svg_str = _inject_hex_data_attrs(svg_str, hex_attr_map)
    return svg_str


def _inject_hex_data_attrs(svg_str: str, hex_attr_map: dict) -> str:
    for skill_id, (skill_name, state) in hex_attr_map.items():
        old = 'id="hex-{}"'.format(skill_id)
        new = ('id="hex-{}" data-skill="{}" data-state="{}" class="hex-group"'
               .format(skill_id, skill_name.replace('"', '&quot;'), state))
        svg_str = svg_str.replace(old, new, 1)
    return svg_str


# ---------------------------------------------------------------------------
# YAML / graph helpers
# ---------------------------------------------------------------------------

def yaml_from_filepath(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)


def yaml_from_string(stringy):
    return yaml.safe_load(stringy)


def read_skills_from_yaml(data):
    return data.get('skills', [])


def read_deps_from_yaml(data):
    return data.get('deps', [])


def read_config_from_yaml(data):
    config = data.get('config', {}) or {}
    # Web rendering defaults: colourful, no tickbox
    return Config(config.get('blackAndWhite', False),
                  config.get('withTickBox', False))


def get_graph_from_data(data):
    skills = read_skills_from_yaml(data)
    deps = read_deps_from_yaml(data)
    if not deps:
        return generate_graph_sequels(skills)
    return generate_graph(deps, skills)


def generate_graph(deps, skills):
    G = nx.DiGraph()
    for node in skills:
        G.add_node(node['name'])
    for dep in deps:
        G.add_edge(dep['from'], dep['to'])
    return G


def generate_graph_sequels(skills):
    G = nx.DiGraph()
    for node in skills:
        G.add_node(node['name'])
        if 'sequels' in node:
            for seq in node['sequels']:
                G.add_node(seq)
                G.add_edge(node['name'], seq)
    return G


def compute_sources(G):
    return [s for s in G.nodes if G.in_degree(s) == 0]


def prep_results_folder():
    path = os.path.join(".", "results")
    try:
        shutil.rmtree(path)
    except OSError:
        pass
    os.makedirs(path, exist_ok=True)


# ---------------------------------------------------------------------------
# Legacy entry points
# ---------------------------------------------------------------------------

def file_to_svgs(file_path):
    data = yaml_from_filepath(file_path)
    return yaml_to_svgs(data)


def string_to_svgs(yaml_str):
    data = yaml_from_string(yaml_str)
    return yaml_to_svgs(data)


def yaml_to_svgs(data):
    config = read_config_from_yaml(data)
    G = get_graph_from_data(data)
    strings = list(G.nodes)
    row, col = HexGrid.bestCount(len(strings))
    content_size = row * col
    grid = HexGrid(50, row, col)
    for _ in range(content_size - len(strings)):
        strings.append("___")
    prep_results_folder()
    results = []
    for seed in range(1, 4):
        score, best = hill_climb(strings, G, grid, evaluation, seed)
        if score > -10:
            svg = draw_skill_tree(best, G, grid, config)
            results.append(svg)
    return results


if __name__ == "__main__":
    data = yaml_from_filepath('arbre-5N6.yaml')
    results = yaml_to_svgs(data)
    for result in results:
        print(result)
