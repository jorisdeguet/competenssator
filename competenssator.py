import math
import os
import random
import shutil
from datetime import datetime
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF

import networkx as nx
import svgwrite
import yaml
from itertools import permutations

# TODO throw exceptions if config is not there
# TODO throw exceptions if in/out degree of one particular node is too high > 6
# TODO throw exceptions if there are cycles
# TODO throw exception if there is no graph with all adjacent edges
# TODO add patterns to black and white styles and gradients :: polka, white, grey, black,

# add a color or black and white setting
backgroundColor = "rgb(255,255,255)"
lightColor = "rgb(230,230,230)"
darkColor = "rgb(10,10,10)"

polkaUrl = ""
gradientUrl = ""

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
            return  diffCol == 1
        elif diffRow > 1:
            return False
        elif diffRow == 1:
            if diffCol == 0:
                return True
            elif rowA % 2 == 0:
                return colA - colB == 1
            elif rowA % 2 == 1:
                return colB - colA == 1
        else:
            return False
    def distance(self, indexA, indexB):
        if self.areIndexConnected(indexA, indexB):
            return 0
        else:
            indexA, indexB = (min(indexA, indexB), max(indexA, indexB))
            rowA, colA = (self.rowFor(indexA), self.colFor(indexA))
            rowB, colB = (self.rowFor(indexB), self.colFor(indexB))
            diffRow = abs(rowA - rowB)
            diffCol = abs(colA - colB)
            return diffRow + diffCol + 1
    @staticmethod
    def bestCount(size):
        tailles = [(2, 3), (3, 4), (4, 5), (5, 6), (6, 8), (7, 10), (8, 11), (9, 12)]
        for (row, col) in tailles:
            if row * col >= size:
                return (row, col)


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
    if current_segment:  # Append the last segment
        segments.append(current_segment)
    return segments

def styles(config):
    styles = []
    if config.blackAndWhite:
        styles.append(Style(darkColor, lightColor))
        styles.append(Style(lightColor, darkColor))
        styles.append(Style(darkColor, "#eee", polkaUrl))
        styles.append(Style(darkColor, "#fff", gradientUrl))
        styles.append(Style(darkColor, "#aaa"))
        styles.append(Style(lightColor, "#444"))

        # black on white, white on black, white on darkgrey, black on lightgrey, polka dots, gradient
        for width in range(2,4):
            for inverted in [True, False]:
                for dashy in [1, 5, 10]:
                    style = Style( "black", "white" )
                    style.stroke_dasharray = dashy
                    style.number_of_strokes = width
                    style.fillColor = darkColor if inverted else lightColor
                    style.strokeColor = lightColor if inverted else darkColor
                    if width != 1 and dashy != 1:
                        continue
                    styles.append(style)
    else:
        colors = ["aquamarine", "lightblue", "lightgreen", "tomato", "lightyellow", "lightpink", "lightgrey"]
        for width in range(1,4):
            for color in colors:
                style = Style( "black", "white")
                style.stroke_dasharray = 1
                style.number_of_strokes = 1
                style.stroke = darkColor
                style.fillColor = color
                styles.append(style)
    return styles

def styleFor(element, parts, config):
    toutes =  styles(config)
    indexOfPart = find_part_containing(element, parts)
    return toutes[indexOfPart % len(toutes)]

def draw_hexagon(dwg, center_x, center_y, grid, text, style, config):
    if text == "___":
        return
    stroke_width = 3
    number_of_strokes = style.number_of_strokes
    perimeters = [1.0, .85, .7]
    perimeters = perimeters[0:number_of_strokes]
    # for the checkbox
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
                xBox, yBox = (center_x + grid.size*.8 * math.cos(angle_rad) * perimeter,
                              center_y + grid.size*.8 * math.sin(angle_rad) * perimeter)
            points.append((x, y))
        for i in range(6):
            x1, y1 = points[i]
            x2, y2 = points[(i + 1) % 6]
            x3, y3 = points[(i + 2) % 6]
            x21, y21 = roundPercent * x1 + (1-roundPercent) * x2, roundPercent * y1 + (1-roundPercent) * y2
            x23, y23 = (1-roundPercent) * x2 + roundPercent * x3, (1-roundPercent) * y2 + roundPercent * y3
            if path == "":
                path += "M " + str(x21) + "," + str(y21)
            else:
                path += " L " + str(x21) + "," + str(y21)
            path += " Q " + str(x2) + "," + str(y2) + " " + str(x23) + "," + str(y23)
        path += " Z"
        if (style.stroke_dasharray == 1):
            print(style.fillColor, style.strokeColor, "<",style.fillUrl,">")
            dwg.add(dwg.path(d=path,
                             fill=style.fillColor if style.fillUrl == "" else style.fillUrl,
                             stroke=style.strokeColor,
                             stroke_width=stroke_width / number_of_strokes,
                             stroke_linecap="round"))
        else:
            dwg.add(dwg.path(d=path,
                             fill=style.fillColor if style.fillUrl == "" else style.fillUrl,
                             stroke=style.strokeColor,
                         stroke_width=stroke_width/number_of_strokes,
                         stroke_dasharray=str(style.stroke_dasharray)+","+str(style.stroke_dasharray),
                         stroke_linecap="round"))
    if config.withTickBox:
        points = []
        points2 = []
        for i in range(6):
            angle_rad = math.radians(30 + 60 * i)
            x, y = xBox + grid.size/11 * math.cos(angle_rad), yBox + grid.size/11 * math.sin(angle_rad)
            x2, y2 = xBox + grid.size/9 * math.cos(angle_rad), yBox + grid.size/9 * math.sin(angle_rad)
            points.append((x, y))
            points2.append((x2, y2))
            # dwg.add(dwg.circle(center=(x, y), r=2, fill='red'))
        dwg.add(dwg.polygon(points2, fill=darkColor))
        dwg.add(dwg.polygon(points, fill='white'))
    draw_text_multiline(center_x, center_y, dwg, grid, style, text)


def draw_text_multiline(center_x, center_y, dwg, grid, style, text):
    lines = split_string_by_length(text, 13)
    # define a style for outlined text
    # strokeColor = "#eee"
    # fillColor = "#333"
    baseStyle = "font-family:Arial Black,Verdana,Arial;font-weight:900;stroke-width:"
    styleSVG = baseStyle + str(
        grid.size * 0.009) + ";stroke:" + style.fillColor + ";font-size:" + str(
        grid.size * 0.17) + ";text-anchor:middle;"
    style2SVG = (baseStyle + str(grid.size * 0.03) +
                 ";stroke:" + style.strokeColor + ";font-size:" + str(grid.size * 0.17) + ";text-anchor:middle;")
    for i, line in enumerate(lines):
        lineheight = grid.size / 4

        text_element = dwg.text(line,
                                insert=(center_x, center_y - grid.size / 3 + lineheight * i),
                                style=style2SVG,
                                transform="rotate(-30, " + str(center_x) + ", " + str(center_y) + ")")
        # text_element.add(dwg.tspan(line, dx=[0], dy=[(10*i)] ))
        dwg.add(text_element)
        text_element = dwg.text(line,
                                insert=(center_x, center_y - grid.size / 3 + lineheight * i),
                                style=styleSVG,
                                transform="rotate(-30, " + str(center_x) + ", " + str(center_y) + ")")
        dwg.add(text_element)


def find_part_containing(element, parts):
    res = 0
    for part in parts:
        if element in part:
            return res
        res += 1
    return res


def draw_skill_tree(skills, G, grid, config):
    global polkaUrl, gradientUrl
    file_name = "results/" + str(datetime.now()) + ".svg"
    dwg = svgwrite.Drawing(
        filename=file_name,
        profile='full',
        size=(str(grid.size * (2*grid.colCount+ 1) ), str(grid.size * (2*grid.rowCount+.5))))
    # create a radial gradient from white to dark grey
    radial = dwg.defs.add(dwg.radialGradient((0.5, 0.5), r=.6, fx=0.5, fy=0.5))
    radial.add_stop_color(offset='0%', color='#000')
    radial.add_stop_color(offset='100%', color='#fff')

    # add a polka dot background
    polka = dwg.defs.add(dwg.pattern(id="polka", size=(10, 10), patternUnits="userSpaceOnUse", patternTransform="rotate(30)"))
    polka.add(dwg.circle(center=(5, 5), r=2, fill='#aaa'))
    polkaUrl = polka.get_funciri()
    gradientUrl = radial.get_funciri()
    dwg.add(
        dwg.rect(
            insert=(0, 0),
            size=('100%', '100%'),
            rx=None, ry=None,
            fill="white"
        )
    )


    parts = list(nx.connected_components(G.to_undirected()))
    for element in skills:
        # find the part containing the skill named element
        index = skills.index(element)
        (row, col) = grid.rowAndColFor(index)
        x = grid.size * (2 * col + (0 if row % 2 == 0 else 1) + 1)
        y = grid.size *  (0.5 + row * math.sqrt(3) + math.sqrt(3) / 2)
        style = styleFor(element, parts, config)
        draw_hexagon(dwg, x, y, grid, element, style, config)
    # add arrows for dependencies
    marker = dwg.defs.add(
        dwg.marker(insert=(1, 1), size=(2, 2), orient='auto', markerUnits='strokeWidth', id='arrowhead'))
    marker.add(dwg.path(d='M0,0 L0,2 L2,1 z', fill='black'))
    marker2 = dwg.defs.add(
        dwg.marker(insert=(1, 1), size=(2, 2), orient='auto', markerUnits='strokeWidth', id='arrowhead2'))
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
        xStart, yStart = (x1 + (x2 - x1)* 2/5, y1 + (y2 - y1) * 2/5)
        xEnd, yEnd = (x1 + (x2 - x1) * 3/5, y1 + (y2 - y1) * 3/5)
        # draw an arrow at the third of the line
        dwg.add(dwg.line(start=(xStart, yStart), end=(xEnd, yEnd), stroke="black", stroke_width=5,
                         stroke_linecap='round', marker_end=marker.get_funciri()))
        dwg.add(dwg.line(start=(xStart, yStart), end=(xEnd, yEnd), stroke="white", stroke_width=3,
                         stroke_linecap='round', marker_end=marker2.get_funciri()))
    dwg.save()
    drawing = svg2rlg(file_name)
    renderPDF.drawToFile(drawing, "./results/file.pdf")
    return dwg.tostring()



def yaml_from_filepath(file_path):
    with open(file_path, 'r') as file:
        data = yaml.safe_load(file)
        return data

def yaml_from_string(stringy):
    data = yaml.safe_load(stringy)
    return data

def read_skills_from_yaml(data):
    return data.get('skills', [])

def read_deps_from_yaml(data):
    return data.get('deps', [])



def evaluation(individual, G, grid):
    asList = list(individual)
    score = 0
    for (a,b) in G.edges:
        score -= grid.distance(asList.index(a), asList.index(b))*10

    # TODO compute if sources are at the top
    sources = compute_sources(G)
    for source in sources:
        row = grid.rowFor(asList.index(source))
        if row != 0:
            score -= row * 0.1
    return score

def hill_climb(strings, G, grid, evaluationFunction, seed):
    random.seed(seed)
    evaluated = []
    perm = permutations(strings)
    population = []
    # Print the obtained permutations
    for i in perm:
        indiv = list(i)
        random.shuffle(indiv)
        population.append(indiv)
        if len(population) == 10:
            break
    # generations
    bestScore = -1000
    scoreHistory = [bestScore]
    bestIndividual = strings
    counter = 0
    while bestScore != 0 and counter < 20000:
        previousBestIndividual = bestIndividual
        counter += 1
        evaluated = {}
        for individual in population:
            score = evaluationFunction(individual, G, grid)
            if score > bestScore or score == 0:
                bestScore = score
                bestIndividual = individual
                scoreHistory.append(bestScore)
                # print("generation " + str(generation) + "  best score " + str(bestScore))
            evaluated[str(individual)] = score
        # Keep the best 10
        population.sort(key=lambda x: evaluated[str(x)], reverse=True)
        # for the top scorer, try all inversions
        population.clear()
        if previousBestIndividual == bestIndividual:
            break
        population.append(bestIndividual)
        for a in range(0, len(bestIndividual)):
            for b in range(a + 1, len(bestIndividual)):
                newby = bestIndividual.copy()
                newby[a], newby[b] = newby[b], newby[a]
                population.append(newby)
    return bestScore, bestIndividual

def file_to_svgs(file_path):
    data = yaml_from_filepath(file_path)
    return yaml_to_svgs(data)
def string_to_svgs(yaml):
    data = yaml_from_string(yaml)
    return yaml_to_svgs(data)


def read_config_from_yaml(data):
    config = data.get('config', [])
    return Config(config.get('blackAndWhite', True), config.get('withTickBox', True))


def yaml_to_svgs(data):
    config = read_config_from_yaml(data)
    #print("Config: " + str(config.blackAndWhite) + " " + str(config.withTickBox))
    G = get_graph_from_data(data)
    # sources = compute_sources(G)
    strings = []
    for node in G:
        strings.append(node)
    # compute the best combo sizes for the number of skills
    (row, col) = HexGrid.bestCount(len(strings))
    contentSize = row * col
    grid = HexGrid(50, row, col)
    # pad the grid with placeholders for empty hexagons
    for i in range(0, contentSize - len(strings)):
        strings.append("___")

    prep_results_folder()
    results = []
    for round in range(1, 10):
        bestScore, bestIndividual = hill_climb(strings, G, grid, evaluation, round)
        print("best score " + str(bestScore))
        # print("best individual " + str(bestIndividual))
        if bestScore > -10:
            svg = draw_skill_tree(bestIndividual, G, grid, config)
            results.append(svg)
    return results


def get_graph_from_data(data):
    skills = read_skills_from_yaml(data)
    deps = read_deps_from_yaml(data)
    G = None
    if deps == None or len(deps) == 0:
        G = generate_graph_sequels(skills)
    else:
        G = generate_graph(deps, skills)
    return G


def prep_results_folder():
    path = os.path.join(".", "results")
    try:
        shutil.rmtree(path)
    except OSError as e:
        print("Error: %s - %s." % (e.filename, e.strerror))
    # create a folder for the svg files
    try:
        os.mkdir(path)
    except OSError as error:
        print(error)


def compute_sources(G):
    sources = []
    for s in G.nodes:
        predCount = sum(1 for dummy in G.predecessors(s))
        succCount = sum(1 for dummy in G.successors(s))
        # print("   connection size " + str(predCount + succCount) + "  " + s["name"])
        if predCount + succCount > 6:
            print("ALERT ALERT ALERT Too many connecting ones ")
        if predCount == 0:
            sources.append(s)
            # print("Source " + s["name"])
    # print("Sources: " + str(sources))
    return sources

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

if __name__ == "__main__":
    file_path = 'arbre-5N6.yaml'
    data = yaml_from_filepath(file_path)
    results = yaml_to_svgs(data)
    for result in results:
        print(result)


    # draw_skill_tree(50, bestIndividual, G, row, col)

