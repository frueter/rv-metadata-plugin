from PySide2.QtGui import QGuiApplication
from rv import commands, rvtypes


METADATA_KEY_COORDINATES = "EXIF/Make"
METADATA_KEY_LOCATIONS = "EXIF/Artist"


class Package_MetadataFinder(rvtypes.MinorMode):

    def __init__(self):
        rvtypes.MinorMode.__init__(self)

        globalBindings = [("pointer-2--push", self.pointerEvent, "Middle mouse button click")]
        localBindings = None

        self.init("Package_MetadataFinder", globalBindings, localBindings)

    def pointerEvent(self, event):
        """
        Callback function that uses the pointer position to find the image coordinates and puts it
        in the system clipboard
        """

        pointer = event.pointer()
        # The name of the image in the sequence for rv
        sourceName = commands.sourceAtPixel(pointer)[0]['name']

        # Tuple containing the coordinates of the point event with regards to the image,
        # where the lower left corner of the image is (0,0)
        imgPointerCoords = commands.eventToImageSpace(sourceName, pointer)

        # An array of image attribute name/value pairs at the current frame
        imgAttributes = commands.sourceAttributes(sourceName)

        try:
            coords, locations = obtainQuadrantData(imgAttributes)
        except TypeError:
            return

        # We need to find the pixel value of the image height
        highestPixelValue = findHighestYPixel(coords)

        # We then convert the RV pointer data to pixels
        pointerPixelCoords = getPointerPixelValue(imgPointerCoords, highestPixelValue)

        found_location = matchPointerToLocation(coords, locations, pointerPixelCoords)
        print(found_location)

        # Copy the matched location to the clipboard
        QGuiApplication.clipboard().setText(found_location)


def createMode():
    return Package_MetadataFinder()


def obtainQuadrantData(imgAttributes):
    """
    Looks into the imageAttributes to obtain the coordinates of each image on the contact sheet, and the
    corresponding locations on disk.
    It returns the values in two lists with the correct format.

    Args:
        imgAttributes (list): List of tuples containing the keys and values of the JPEG image attributes.

    Returns: (tuple) The quadrant data from the image JPEG attributes as follows:
            ( [coords1, coord2, ], [location_on_disk1, location_on_disk2, ] )

    """
    coord_string = None
    location_string = None

    for key, value in imgAttributes:
        if key == METADATA_KEY_COORDINATES:
            coord_string = value
        if key == METADATA_KEY_LOCATIONS:
            location_string = value

    if not coord_string or not location_string:
        print("Unable to obtain the coordinate values, image does not follow metadata format")
        return

    coords_str = coord_string.split(';')
    coords = [format_coordinate(coord) for coord in coords_str]

    locations = location_string.split(';')

    return coords, locations


def format_coordinate(coord_string):
    """
    This function converts a string with two coordinate values into a tuple of float coordinate values

    Args:
        coord_string: (str) The pixel coordinates. Eg.: '0,0,1024,1024'

    Returns: (tuple) a tuple where the first element represents the x axis and the second
             element represents the y axis. Eg.: ([0.0, 0.0], [1024.0, 1024.0])

    """

    all_coord_list = coord_string.split(",")
    all_coord_list = [float(i) for i in all_coord_list]
    formatted_coord = all_coord_list[:2], all_coord_list[2:]

    return formatted_coord


def findHighestYPixel(coord_list):
    """
    Given a list containing pixel coordinate values, returns the highest 'y' value

    Args:
        coord_list: list of tuples containing the lower and top corner of a quadrant
                    Eg.: [([0.0, 0.0], [1024.0, 1024.0]), ([1024.0, 0.0], [2048.0, 1024.0]), ]

    Returns: float

    """
    y_list = []

    for lower_corner, top_corner in coord_list:
        x, y = top_corner
        y_list.append(y)

    return max(y_list)


def getPointerPixelValue(imgPointerCoords, pixelHeight):
    """
    Converts the pointer values from RV into pixel values.
    The pointer data from RV (imgPointerCoords) is a tuple were the lower left corner of the image is (0,0),
    the height of the image is 1 and the width varies depending on the image aspect.
    Knowing the highest pixel value allows us to define the '1' ratio.

    Args:
        imgPointerCoords: (tuple) RV pointer location
        pixelHeight: (float) The highest 'y' pixel value

    Returns: tuple

    """
    pointer_x, pointer_y = imgPointerCoords
    pixel_x = pixelHeight * pointer_x

    # Because the RV defines the pointer values from the lower left instead of the upper left corner, we need
    # to invert the 'y' values.
    revert_y_pointer = abs(pointer_y - 1)
    pixel_y = pixelHeight * revert_y_pointer

    return pixel_x, pixel_y


def matchPointerToLocation(coords, locations, pointerPixelCoords):
    """
    This function matches the pointer position to a image quadrant and it returns the corresponding
    location string from the locations list

    Args:
        coords: (list) All the quadrants coordinates of the images in pixels
        locations: (list) Strings with the locations on disk of the contact sheet images
        pointerPixelCoords: (tuple) The pointer coordinates converted to pixels

    Returns: (str)

    """
    found_location = None
    pointer_x, pointer_y = pointerPixelCoords

    for coord, location in zip(coords, locations):
        lower_corner, top_corner = coord
        is_inside = (lower_corner[0] < pointer_x < top_corner[0]) and (lower_corner[1] < pointer_y < top_corner[1])
        if is_inside:
            found_location = location

    return found_location
