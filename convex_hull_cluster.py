# @Author: Joey Teng <Toujour>
# @Date:   20-Nov-2017
# @Email:  joey.teng.dev@gmail.com
# @Filename: convex_hull_cluster.py
# @Last modified by:   Toujour
# @Last modified time: 24-Jan-2018
"""
Input argument list:
    dataset_filename
    clusters_filename
    output_filename
    log_file(optional)
Predefined types:
    Point: <'dict'>
        {'coordinate': (float, ...), 'label': int}

    Dataset: <'list'>
        list of dict objects:
        [Point, ...]

    Vertex: <'tuple'>
        Point['coordinate']

    Vertices: <'list'>
        [Vertex, ...]
"""

import json
import logging
import logging.handlers
import queue
import sys

import numpy


def initialize_logger(filename=None, level=logging.INFO, filemode='w'):
    """
    Initialize a logger in module logging
    """
    log_format = '%(asctime)s %(levelname)s\n' + \
        '  %(filename)s:%(lineno)s: %(name)s %(message)s'

    if filename is None:
        handler = logging.StreamHandler()
    else:
        handler = logging.handlers.RotatingFileHandler(
            filename=filename, mode=filemode)

    handler.setFormatter(logging.Formatter(log_format))
    logger = logging.getLogger('LOG')
    logger.addHandler(handler)
    logger.setLevel(level)

    return logger


def load_dataset(filename):
    """
    Parameters:
        filename: path of input file.
            CSV format
            [coordinate, ...] + [label]

    Returns:
        dataset:
            <type>: Dataset
    """
    return [(lambda point: {
        'coordinate': tuple(map(float, point[:-1])),
        'label': int(point[-1])})(string.split(','))
        for string in open(filename, 'r').read().split('\n')]


def signed_volume(vertices):
    """
    Description:
        Calculate the signed volume of n-dimensional simplex
            defined by (n + 1) vertices
        Reference:
            Wedge Product: http://mathworld.wolfram.com/WedgeProduct.html

    Parameters:
        vertices:
            <type>: Vertices

    Returns:
        sign : (...) array_like
            A number representing the sign of the determinant. For a real
                matrix, this is 1, 0, or -1. For a complex matrix, this is a
                complex number with absolute value 1 (i.e., it is on the unit
                circle), or else 0.
        logdet : (...) array_like
            The natural log of the absolute value of the determinant.

        If the determinant is zero, then sign will be 0 and logdet will be
        -Inf. In all cases, the determinant is equal to sign * np.exp(logdet).

        Reference:
            From scipy manual
                https://docs.scipy.org/doc/numpy-1.13.0/reference/generated/numpy.linalg.slogdet.html#numpy.linalg.slogdet
    """
    reference = numpy.array(vertices[0])
    (sign, logvolume) = numpy.linalg.slogdet(numpy.matrix(
        [numpy.array(x) - reference for x in vertices[1:]]))
    return (sign, logvolume)


def squared_area(vertices):
    """
    Description:
        Calculate the squared area of (n - 1)-dimensional simplex defined by
            n vertices in n-dimensional space
        Reference:
            Wedge Product: http://mathworld.wolfram.com/WedgeProduct.html

    Parameters:
        vertices:
            <type>: Vertices

    Returns:
        logdet : (...) array_like
            The natural log of the absolute value of the determinant.

        If the determinant is zero, then sign will be 0 and logdet will be
        -Inf. In all cases, the determinant is equal to sign * np.exp(logdet).

        Reference:
            From scipy manual
                https://docs.scipy.org/doc/numpy-1.13.0/reference/generated/numpy.linalg.slogdet.html#numpy.linalg.slogdet
    """
    reference = numpy.array(vertices[0])
    matrix = numpy.matrix([numpy.array(x) - reference for x in vertices[1:]])
    logvolume = numpy.linalg.slogdet(matrix.T * matrix)[1]  # sign, logvolume
    return logvolume


def check_inside(face=None, pivot=None, edge=None, area=None):
    """
    Description
    Parameters:
        face:
        pivot:
            <type>: Vertex
        edge:
            Default:
                face[:-1]
        area:
            Default:
                squared_area(face)
    Returns:
        inside:
            <type>: bool
        face:
            new face generated with (edge + pivot)
        area:
            new squared_area calculated using _face
    """
    if face is None or pivot is None:
        raise ValueError("Wrong parameters given")
    edge = edge or face[:-1]
    area = area or squared_area(face)

    sign, logvolume = signed_volume(form_face(face, pivot))
    _face = form_face(edge, pivot)
    _area = squared_area(_face)
    if (numpy.isclose([logvolume], [0]) and _area > area) or sign < 0:
        # outside
        return (False, _face, _area)
    return (True, _face, _area)


def check_inside_hull(hull, pivot):
    """
    Description:
    Parameters:
    Returns:
        inside:
            <type>: bool
    """
    for face in hull:
        if not check_inside(face=face, pivot=pivot):
            return False
    return True


def pivot_on_edge(dataset, edge, label):
    """
    Description:
    Parameters:
        dataset:
            <type>: Dataset

        edge:
            <type>: Vertices

        label:
            <type>: Point['label']
    Recieve:
    Yields:
    Returns:
    """
    index = 0
    length = len(dataset)
    while index < length and dataset[index]['label'] != label:
        index += 1

    homo = {}
    homo['pivot'] = dataset[index]['coordinate']
    homo['face'] = form_face(edge, homo['pivot'])
    homo['area'] = squared_area(homo['face'])

    while index < length and dataset[index]['label'] == label:
        index += 1

    opp = {}
    opp['pivot'] = dataset[index]['coordinate']
    opp['face'] = form_face(edge, opp['pivot'])
    opp['area'] = squared_area(opp['face'])

    found = False
    check = yield [homo['pivot'], label, None]
    if check == 'homogeneous':  # not 'hetrogeneous'
        found = True

    for point in dataset:
        current = {}
        current['pivot'] = point['coordinate']
        updated, current['face'], current['area'] = check_inside(
            face=homo['face'], pivot=current['pivot'],
            edge=edge, area=homo['area'])
        if point['label'] == label:
            updated = not updated  # update only when new pivot is outer

        if updated:
            check = yield [current['pivot'], label, None]
            if check == 'homogeneous':  # not 'hetrogeneous'
                # update
                homo = current
                found = True
            elif check == 'opposite inside':  # not 'opposite outside'
                # update pivots with opposite label
                opp = current

    yield (homo['pivot'], found)
    return


def form_face(edge, pivot):
    """
    Description
    Parameters:
        edge:
            <type>: Vertices
        pivot:
            <type>: Point['coordinate']
    """
    return tuple(list(edge) + [pivot])


def qsort_partition(data, target=1, lhs=0, rhs=None):
    """
    Description:
        Find the smallest [target] values in the [data] using [comp] as __lt__

    Complexity:
        O(n)

    Parameters:
        data:
            <type>: Dataset

        target:
            int
            [terget] smallest values will be returned.
            (default=1, smallest value will be returned in a list
        lhs:
            lowest index (default=0)
        rhs:
            highest index + 1 (default=len(data))
        comp: # Currently unavailable
            cumstomised function used for comparing
            default=__builtin__.__lt__

    Returns:
        list which contains [target] shallow copies of elements['coordinate']
    """
    lhs = lhs or 0
    rhs = (rhs or len(data)) - 1
    # comp is Partially supported: only used in partitioning
    # but not in sorting return values
    comp = (lambda x, y: x < y)

    _data = []
    label = data[0]['label']
    for element in data[lhs:rhs]:
        if element['label'] == label:
            _data.append(element['coordinate'])
    data = _data

    position = -1

    while position != target:
        if position < target:
            lhs = position + 1
        elif position > target:
            rhs = position - 1

        pivot = data[rhs]
        index = lhs
        for i in range(lhs, rhs):
            if comp(data[i], pivot):
                data[i], data[index] = data[index], data[i]
                index += 1
        data[pivot], data[index] = data[index], data[pivot]
        position = index  # Return value

    return (label, data[:position].sort())


def initialize_hull(dataset):
    """
    Description
    Parameters:
        dataset:
            <type>: Vertices
    Returns:
        label:
        edge
    """
    dimension = len(dataset[0]['coordinate'])
    label, edge = qsort_partition(dataset, target=dimension - 1)
    return (label, tuple(edge))


def queuing_face(face, _queue):
    """
    Description
    Parameters:
        face:
            <type>: Vertices
        _queue:
    """
    for i in range(len(face)):
        sub_face = []
        for j, element in enumerate(face):
            if i != j:
                sub_face.append(element)
        _queue.put(tuple(sub_face))


def check_homogeneity(dataset, hull, label, used_pivots):
    """
    Description:
    Parameters:
        dataset:
        hull:
        label:
        used_pivots:
            <type>: dict
                {Vertex: True}
    Returns:
        homogeneity:
            <type>: bool
    """
    for point in dataset:
        pivot = point['coordinate']
        _label = point['label']
        if pivot in used_pivots or _label == label:
            continue
        if check_inside_hull(hull, pivot):
            return False

    return True


def gift_wrapping(dataset):
    """
    Description:
    Parameters:
        dataset:
    Returns:
        <type>: dict
            {
                "faces": all the faces,
                    <type>: list
                    [face]
                "vertices": all the vertices
                    <type>: dict
                    {Vertex: True}
            }
    Reference: https://www.cs.jhu.edu/~misha/Spring16/09.pdf
    """
    label, face = initialize_hull(dataset)
    _queue = queue.Queue()
    queuing_face(face, _queue)

    processed = {}

    hull = []
    hull.append(face)
    vertices = [coordinate for coordinate in face]
    used_pivots = dict(zip(face, [True] * len(face)))
    edge = None
    while _queue.not_empty:
        last_edge = edge
        edge = _queue.get()
        if not processed.get(edge, d=False):
            find_pivot = pivot_on_edge(dataset, edge, label)
            pivot = next(find_pivot)
            while len(pivot) == 3:
                # Find next pivot
                # Feedback: if the pivot suggested is a valid choice
                if label == pivot[1]:
                    hull.append(form_face(edge, pivot[0]))
                    homogeneity = check_homogeneity(
                        dataset, hull, label, used_pivots)
                    hull.pop()
                    if homogeneity:
                        pivot = find_pivot.send('homogeneous')
                    else:
                        pivot = find_pivot.send('hetrogeneous')
                else:
                    inside = check_inside_hull(hull, pivot[0])
                    if inside:
                        pivot = find_pivot.send('opposite inside')
                    else:
                        pivot = find_pivot.send('opposite outside')

            pivot, found = pivot
            if not found:
                pivot = vertices[0]
                edge = last_edge
                hull.pop()
                vertices.pop()

            face = form_face(edge, pivot)
            vertices.append(pivot)
            used_pivots[pivot] = True
            hull.append(face)
            queuing_face(face, _queue)
            processed[edge] = True

    return {
        "faces": hull,
        "vertices": used_pivots}


def calculate_volume(hull):
    """
    Description:
    Parameter:
        hull:
    Return:
    """
    origin = hull[0][0]
    volume = 0.0
    for face in hull:
        logvolume = signed_volume(form_face(face, origin))[1]
        volume += numpy.e ** logvolume

    return volume


def clustering(dataset):
    """
    Description:
        Convex Hull Algorithm - modified
        Base on Gift Wrapping
        All hulls will be pure(only contains data points with same label)

    Parameters:
        dataset:
            list of dict objects:
            [Point, ...]

    Returns:
        clusters:
            list of dict objects:
            [{'vertices': [Vertex, ...],
              'points': [Vertex, ...](vertices are excluded)
              'size':
                    <type>: int
                    len(['vertices']) + len(['points']),
              'volume': float(optional)}, ...]
    """
    clusters = []
    while dataset:
        # List is not empty
        cluster = gift_wrapping(dataset)

        hull = cluster['faces']
        used_vertices = cluster['vertices']
        _dataset = []
        vertices = []
        points = []
        for point in dataset:
            vertex = point['coordinate']
            if vertex in used_vertices:
                vertices.append(vertex)
            else:
                _dataset.append(point)
                if check_inside_hull(hull, vertex):
                    points.append(vertex)
        volume = calculate_volume(hull)

        dataset = _dataset
        clusters.append({'vertices': vertices,
                         'points': points,
                         'size': len(vertices) + len(points),
                         'volume': volume})

    return clusters


def size_versus_number_of_clusters(clusters):
    """
    Description
    """
    # TODO: size versus number of clusters
    # return None
    return clusters[0]['size']


def volume_versus_size(clusters):
    """
    Description
    """
    # TODO: volume versus size
    # return None
    return clusters[0]['volume']


def main(argv):
    """
    main
    """
    dataset_filename, clusters_filename, output_filename, log_file = tuple(
        argv)

    logger = initialize_logger(log_file)
    logger.info('Start')
    logger.debug('Logger initialized')
    logger.debug('sys.argv: %r', sys.argv)

    logger.debug('Loading dataset')
    dataset = load_dataset(dataset_filename)
    logger.info('Dataset loaded')

    logger.debug('Clustering data points')
    clusters = clustering(dataset)
    logger.debug(
        'Dumping clusters data into json file: %s', clusters_filename)
    json.dump(clusters, open(clusters_filename, 'w'))
    logger.info('Data points clustered')

    logger.debug('Calculating meta-feature indicators')
    features = {'Number of Clusters': len(clusters),
                'Size versus Number of Clusters':
                size_versus_number_of_clusters(clusters),
                'Volume versus Size': volume_versus_size(clusters)}
    logger.debug(
        'Dumping meta-feature indicators into json file: %s',
        clusters_filename)
    json.dump(features, open(output_filename, 'w'))
    logger.info('Meta-feature indicators calculated')

    logger.info('Completed')


if __name__ == '__main__':
    main(sys.argv[1:])
