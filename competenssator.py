import math
import os
import random
import shutil
from datetime import datetime
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF
from enum import Enum

import networkx as nx
import svgwrite
import yaml
from itertools import permutations

# TODO https://docs.render.com/docs/deploy-flask

# add a color or black and white setting
backgroundColor = "rgb(255,255,255)"
lightColor = "rgb(230,230,230)"
darkColor = "rgb(10,10,10)"

class Style:
    def __init__(self, stroke, stroke_width, inverted=False):
        self.stroke = stroke
        self.inverted = inverted
        self.stroke_width = stroke_width
        self.stroke_dasharray = 5
        self.number_of_strokes = 1

class Config:
    def __init__(self, blackAndWhite, withBox):
        self.blackAndWhite = blackAndWhite
        self.withBox = withBox

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

def styles():
    styles = []
    for width in range(1,4):
        for inverted in [True, False]:
            for dashy in [1, 5, 10]:
                style = Style( "black", width, inverted)
                style.stroke_dasharray = dashy
                style.number_of_strokes = width
                if width != 1 and dashy != 1:
                    continue
                styles.append(style)
    return styles

def styleFor(element, parts):
    toutes =  styles()
    indexOfPart = find_part_containing(element, parts)
    return toutes[indexOfPart % len(toutes)]

def distance(indexA, indexB, col):
    if areIndexConnected(indexA, indexB, col):
        return 0
    else:
        indexA, indexB = (min(indexA, indexB), max(indexA, indexB))
        rowA, colA = (indexA // col, indexA % col)
        rowB, colB = (indexB // col, indexB % col)
        diffRow = abs(rowA - rowB)
        diffCol = abs(colA - colB)
        return diffRow + diffCol + 1
def areIndexConnected(indexA, indexB, col):
    indexA, indexB = (min(indexA, indexB), max(indexA, indexB))
    rowA, colA = (indexA // col, indexA % col)
    rowB, colB = (indexB // col, indexB % col)
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

def draw_hexagon(dwg, center_x, center_y, row, col, size, text, style):
    if text == "___":
        return
    stroke_width = 3
    number_of_strokes = style.number_of_strokes
    perimeters = [1.0, 0.95, .9, .85, .8, .75]
    perimeters = perimeters[0:number_of_strokes]
    fillColor = darkColor if style.inverted else lightColor
    strokeColor = lightColor if style.inverted else darkColor
    # for the checkbox
    xBox, yBox = (0, 0)
    for perimeter in perimeters:
        path = ""
        roundPercent = 0.15
        points = []
        for i in range(6):
            angle_rad = math.radians(30 + 60 * i)
            x = center_x + size * math.cos(angle_rad) * perimeter
            y = center_y + size * math.sin(angle_rad) * perimeter
            if i == 0 and perimeter == 1.0:
                xBox, yBox = center_x + size*.8 * math.cos(angle_rad) * perimeter, center_y + size*.8 * math.sin(angle_rad) * perimeter
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
            dwg.add(dwg.path(d=path, fill=fillColor, stroke=strokeColor,
                             stroke_width=stroke_width / number_of_strokes,
                             stroke_linecap="round"))
        else:
            dwg.add(dwg.path(d=path, fill=fillColor, stroke=strokeColor,
                         stroke_width=stroke_width/number_of_strokes,
                         stroke_dasharray=str(style.stroke_dasharray)+","+str(style.stroke_dasharray),
                         stroke_linecap="round"))
    dwg.add(dwg.circle(center=(xBox, yBox), r=4, fill='blue'))
    points = []
    points2 = []
    for i in range(6):
        angle_rad = math.radians(30 + 60 * i)
        x, y = xBox + size/11 * math.cos(angle_rad), yBox + size/11 * math.sin(angle_rad)
        x2, y2 = xBox + size/9 * math.cos(angle_rad), yBox + size/9 * math.sin(angle_rad)
        points.append((x, y))
        points2.append((x2, y2))
        # dwg.add(dwg.circle(center=(x, y), r=2, fill='red'))
    dwg.add(dwg.polygon(points2, fill=darkColor))
    dwg.add(dwg.polygon(points, fill='white'))
    lines = split_string_by_length(text, 13)
    for i, line in enumerate(lines):
        lineheight = size/4
        text_element = dwg.text(line,
                                insert=(center_x, center_y-size/3+lineheight*i),
                                fill=strokeColor,
                                font_family="Arial",
                                font_size=size * 0.17,
                                text_anchor='middle',
                                transform="rotate(-30, " + str(center_x) + ", " + str(center_y) + ")")
        #text_element.add(dwg.tspan(line, dx=[0], dy=[(10*i)] ))
        dwg.add(text_element)


def find_part_containing(element, parts):
    res = 0
    for part in parts:
        if element in part:
            return res
        res += 1
    return res


def draw_skill_tree(size, skills, G, rowCount, colCount):
    # gridsize = math.floor(math.sqrt(len(skills)))
    # name the file with the date and time
    file_name = "results/" + str(datetime.now()) + ".svg"
    dwg = svgwrite.Drawing(
        filename=file_name,
        profile='full',
        size=(str(size * (2*colCount+ 1) ), str(size * (2*rowCount+.5))))
    dwg.add(
        dwg.rect(
            insert=(0, 0),
            size=('100%', '100%'),
            rx=None, ry=None,
            fill=backgroundColor))
    parts = list(nx.connected_components(G.to_undirected()))
    # print("parts " + str(parts))
    for element in skills:
        # find the part containing the skill named element
        index = skills.index(element)
        row = index // colCount
        col = index % colCount
        x = size * (2 * col + (0 if row % 2 == 0 else 1) + 1)
        y = size *  (0.5 + row * math.sqrt(3) + math.sqrt(3) / 2)
        # colors = ["aquamarine", "lightblue", "lightgreen", "tomato"]
        # fillColors = random.randrange(0, len(colors))
        # fillColor = colors[fillColors]
        style = styleFor(element, parts)
        if index == 11:
            fillColor = "red"
        if areIndexConnected(11, index, colCount):
            fillColor = "blue"
        draw_hexagon(dwg, x, y, row, col,  size, element, style)
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
        rowA, colA = (indexA // colCount, indexA % colCount)
        rowB, colB = (indexB // colCount, indexB % colCount)
        x1 = xFor(colA, rowA, size)
        y1 = yFor(rowA, size)
        x2 = xFor(colB, rowB, size)
        y2 = yFor(rowB, size)
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

def yFor(rowA, size):
    return size * (0.5 + rowA * math.sqrt(3) + math.sqrt(3) / 2)

def xFor(colA, rowA, size):
    return size * (2 * colA + (0 if rowA % 2 == 0 else 1) + 1)

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

def bestCount(size):
    tailles = [(2,3), (3, 4), (4, 5), (5, 6), (6, 8), (7, 10), (8, 11), (9, 12)]
    for (row, col) in tailles:
        if row*col >= size:
            return (row, col)

def evaluation(individual, G, col):
    asList = list(individual)
    score = 0
    for (a,b) in G.edges:
        score -= distance(asList.index(a), asList.index(b), col)
    return score

def hill_climb(strings, G, col, evaluationFunction):
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
            score = evaluationFunction(individual, G, col)
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

def yaml_to_svgs(data):
    skills = read_skills_from_yaml(data)
    deps = read_deps_from_yaml(data)
    G = nx.DiGraph()
    for node in skills:
        G.add_node(node['name'])
    for dep in deps:
        G.add_edge(dep['from'], dep['to'])
    sources = []
    for s in skills:
        predCount = sum(1 for dummy in G.predecessors(s["name"]))
        succCount = sum(1 for dummy in G.successors(s["name"]))
        # print("   connection size " + str(predCount + succCount) + "  " + s["name"])
        if predCount + succCount > 6:
            print("ALERT ALERT ALERT Too many connecting ones ")
        if predCount == 0:
            sources.append(s)
            # print("Source " + s["name"])
    print("Sources: " + str(sources))
    strings = []
    for node in skills:
        strings.append(node["name"])
    (row, col) = bestCount(len(strings))
    # print("row " + str(row) + " col " + str(col))
    contentSize = row * col
    for i in range(0, contentSize - len(strings)):
        strings.append("___")
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
    results = []
    for round in range(1, 10):
        bestScore, bestIndividual = hill_climb(strings, G, col, evaluation)
        print("best score " + str(bestScore))
        # print("best individual " + str(bestIndividual))
        if bestScore == 0:
            svg = draw_skill_tree(50, bestIndividual, G, row, col)
            results.append(svg)
    return results

if __name__ == "__main__":
    file_path = '5N6.yaml'
    data = yaml_from_filepath(file_path)
    results = yaml_to_svgs(data)
    for result in results:
        print(result)


    # draw_skill_tree(50, bestIndividual, G, row, col)

