# Andre Gillan
# May 8, 2020
# Below is the software project I completed for the project portion of my Master's degree
# it is an interactive fluid solver based on "Real-time fluid mechanics for games" (Jos Stam, 2003)
# with modifications for color advection/diffusion, temperature for smoke simulation, a toolbox to support
# the user interface, etc.
# please see the document related to the project for more information
# here's the source code, I was able to create a linux executable using pyinstaller but I won't distribute that


#import statements
import sys, os

try:
    import numpy as np
except ImportError:
    print('ERROR: NumPy not installed properly.')
    sys.exit()

try:
    from OpenGL.GLUT import *
    from OpenGL.GL import *
    from OpenGL.GLU import *
except ImportError:
    print('ERROR: PyOpenGL not installed properly.')
    sys.exit()

try:
    os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide" # hides the pygame welcome. Please support PyGame anyway!
    import pygame
except ImportError:
    print('ERROR: PyGame not installed properly.')
    sys.exit()

try:
    import thorpy
except ImportError:
    print('ERROR: ThorPy not installed properly.')
    sys.exit()


# if webbrowser is available, the toolbox contains a button that provides help through the browser
# if import webbrowser doesn't work, the program can still run without the button
try:
    webbrowser_available = True
    import webbrowser
except ImportError:
    print('ERROR: webbrowser import failed. Help button is unavailable')
    webbrowser_available = False

np.set_printoptions(threshold=np.inf)


#####################
# simulation properties
# these are related to the simulation algorithm which is mostly from Jos Stam: "Real-Time Fluid Dynamics for Games"
#####################
simulation_properties = {} # contains parameters necessary for calculating simulation frames, whether changable or not
simulation_data = {} # contains specificly grid data

simulation_properties['dt'] = 0.2
simulation_properties['diff'] = 0.0 # diffusion coefficient
simulation_properties['temp_diff'] = 0 # diffusion coefficient for temperature
simulation_properties['visc'] = 0
simulation_properties['force'] = 5
simulation_properties['dens_source'] = 100.
simulation_properties['temp_source_red'] = 51
simulation_properties['temp_source_green'] = 51
simulation_properties['temp_source_blue'] = 51
simulation_properties['buoyancy'] = 0.01
simulation_properties['smoke_diff_away_red'] = 0.99
simulation_properties['smoke_diff_away_green'] = 0.99
simulation_properties['smoke_diff_away_blue'] = 0.99
simulation_properties['temp_diff_away'] = 0.99
simulation_properties['N'] = 50
simulation_properties['linear_solver_tries'] = 20
simulation_properties['vorticity_confinement_constant'] = 0.005 #NOTE: this was 0.00005 earlier, so this value hasn't been tested as thoroughly
simulation_properties['size'] = simulation_properties['N'] + 2 # size includes two boundaries cells
size = simulation_properties['size']

# for numerical stability reasons, float64 is highly recommended for velocity data
# this is because of the linear algebra solver; I don't know if float64 is necessary for Gauss-Seidel relaxation but it's best to be safe
simulation_data['u'] = np.zeros(shape=(size+1,size+1), dtype=(np.float64))
simulation_data['u_prev'] = np.zeros(shape=(size+1,size+1), dtype=(np.float64))
simulation_data['v'] = np.zeros(shape=(size+1,size+1), dtype=(np.float64))
simulation_data['v_prev'] = np.zeros(shape=(size+1,size+1), dtype=(np.float64))
# smoke density and other things can use float64. But on my machine, float64 is way faster in this Python version of the algorithm.
# In fact, it appears that float128 is just as fast as float64 but I don't think there's a benefit
simulation_data['dens'] = np.zeros(shape=(size,size), dtype=(np.float64))
simulation_data['dens_prev'] = np.zeros(shape=(size,size), dtype=(np.float64))
simulation_data['red_dens'] = np.zeros(shape=(size,size), dtype=(np.float64))
simulation_data['red_dens_prev'] = np.zeros(shape=(size,size), dtype=(np.float64))
simulation_data['green_dens'] = np.zeros(shape=(size,size), dtype=(np.float64))
simulation_data['green_dens_prev'] = np.zeros(shape=(size,size), dtype=(np.float64))
simulation_data['blue_dens'] = np.zeros(shape=(size,size), dtype=(np.float64))
simulation_data['blue_dens_prev'] = np.zeros(shape=(size,size), dtype=(np.float64))
simulation_data['temp'] = np.zeros(shape=(size,size), dtype=(np.float64))
simulation_data['temp_prev'] = np.zeros(shape=(size,size), dtype=(np.float64))

#######################################################
### properties for the thorpy/pygame gui interface #####
### and some things related to the OpenGL window   #####
#######################################################
gui_properties = {}
gui_properties['DOUBLE_CLICK_TIME'] = 500 #milliseconds. 500 milliseconds is the windows default: https://docs.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setdoubleclicktime?redirectedfrom=MSDN
gui_properties['TOOLBOX_COLOR'] = (200,200,200)
gui_properties['TOOLBOX_WIDTH'] = 209
gui_properties['TOOLBOX_HEIGHT'] = 629 + 40*(webbrowser_available) #extra room for a help button if possible
gui_properties['COLOR_BOX_COLORS'] = [(255,255,255),(255,0,0),(0,255,0),(0,0,255)]
gui_properties['COLOR_BOX_RECT_TUPLES'] = [(5,5,45,45), #ordered tuples of rects for color boxes
                                           (55,5,45,45),
                                           (105,5,45,45),
                                           (155,5,45,45)]
gui_properties['SELECTED_COLOR_INDEX_SINGLE_CLICK'] = 0
gui_properties['SELECTED_COLOR_INDEX_DOUBLE_CLICK'] = 0
gui_properties['SELECTED_COLOR'] = gui_properties['COLOR_BOX_COLORS'][0] #this will change according to double click index i.e. this is the color selector color, NOT the smoke color
gui_properties['SMOKE_COLOR'] = gui_properties['COLOR_BOX_COLORS'][0] #this will change according to single click

gui_properties['PYGAME_ELEMENTS'] =  {'rect':[],'line_single_click':[],'line_double_click':[]}
gui_properties['RUNNIG'] = True
gui_properties["COLOR_BOX_EVENT"] = None # stores event on color box for handling double or single clicks
gui_properties['VISC_SLIDER_VALUE'] = 0
gui_properties['SCREEN_WIDTH'] = 750
gui_properties['SCREEN_HEIGHT'] = 750
gui_properties['MOUSE_DOWN'] = [False,False,False]
gui_properties['ORIG_MOUSE_X'] = 0.0  #originating mouse position for click and drag event
gui_properties['ORIG_MOUSE_Y'] = 0.0
gui_properties['MOUSE_X'] = 0.0  #current mouse position
gui_properties['MOUSE_Y'] = 0.0
gui_properties['SCREEN'] = None # The pygame display for the toolbox, this will be populated with pygame_interface()
gui_properties['THORPY_ELEMENTS'] = dict() # to be populated with the Thorpy elements for the toolbox
gui_properties['DISPLAY_VELOCITY'] = False
gui_properties['CLOCK'] = pygame.time.Clock()

#adds a gray rectangle to bottom because I can't call screen fill with a thorpy menu
#must call this before color box rectangles so that it's first in the list of things rects to draw
def bottom_screen_rectangle():
    PYGAME_ELEMENTS,TOOLBOX_COLOR,TOOLBOX_WIDTH = gui_properties['PYGAME_ELEMENTS'],gui_properties['TOOLBOX_COLOR'],gui_properties['TOOLBOX_WIDTH']
    PYGAME_ELEMENTS['rect'].append({'color':TOOLBOX_COLOR,'rect':(0,0,TOOLBOX_WIDTH,53)})

# add color boxes to PYGAME_ELEMENTS
def add_color_boxes():
    COLOR_BOX_COLORS,PYGAME_ELEMENTS,COLOR_BOX_RECT_TUPLES = gui_properties['COLOR_BOX_COLORS'],gui_properties['PYGAME_ELEMENTS'],gui_properties['COLOR_BOX_RECT_TUPLES']
    for i,color in enumerate(COLOR_BOX_COLORS):
        PYGAME_ELEMENTS['rect'].append({'color':color,'rect':COLOR_BOX_RECT_TUPLES[i]})

#draws a black box around the selected color box
# some of this code is extraneous because an earlier version used outlines of other colors as well
def color_box_outline(surface,rect,width=3,color=(20,20,20),line='double_click'):

    PYGAME_ELEMENTS = gui_properties['PYGAME_ELEMENTS']

    PYGAME_ELEMENTS['line_'+line] = [];
    #two adjacent points (including wrap back to beginning) make an edge of the rectangle
    positions = [(rect[0],rect[1]),
                (rect[0]+rect[2],rect[1]),
                (rect[0]+rect[2],rect[1]+rect[3]),
                (rect[0],rect[1]+rect[3])]
    for i in range(len(positions)):
        PYGAME_ELEMENTS['line_'+line].append({'color':color,'start':positions[i],
                                        'end':positions[(i+1)%len(positions)],
                                        'width':width})
    for i in range(len(positions)):
        pygame.draw.line(surface, color, positions[i], positions[(i+1)%len(positions)], width)


# returns True if a position pair is within a 4-tuple defining a pygame rect
def within_rect(pos,rectangle):
    return (rectangle[0] + rectangle[2]) >= pos[0] >= rectangle[0] and (rectangle[1] + rectangle[3]) >= pos[1] >= rectangle[1]


def pygame_interface():

    TOOLBOX_WIDTH,TOOLBOX_HEIGHT,TOOLBOX_COLOR,COLOR_BOX_RECT_TUPLES = gui_properties['TOOLBOX_WIDTH'],gui_properties['TOOLBOX_HEIGHT'],gui_properties['TOOLBOX_COLOR'],gui_properties['COLOR_BOX_RECT_TUPLES']
    SELECTED_COLOR_INDEX_SINGLE_CLICK,SELECTED_COLOR_INDEX_DOUBLE_CLICK = gui_properties['SELECTED_COLOR_INDEX_SINGLE_CLICK'],gui_properties['SELECTED_COLOR_INDEX_DOUBLE_CLICK']

    pygame.init()
    pygame.display.set_caption("Toolbox")

    gui_properties['SCREEN'] = pygame.display.set_mode((TOOLBOX_WIDTH,TOOLBOX_HEIGHT))
    gui_properties['SCREEN'].fill(TOOLBOX_COLOR)

    # double-clickable color boxes for changing smoke color
    # white, red, green, blue
    bottom_screen_rectangle()
    add_color_boxes()
    color_box_outline(gui_properties['SCREEN'],COLOR_BOX_RECT_TUPLES[SELECTED_COLOR_INDEX_DOUBLE_CLICK])



def make_thorpy_interface():
    TE = gui_properties['THORPY_ELEMENTS']
    DOUBLE_CLICK_TIME,TOOLBOX_COLOR,TOOLBOX_HEIGHT,TOOLBOX_WIDTH,COLOR_BOX_COLORS,COLOR_BOX_RECT_TUPLES = gui_properties['DOUBLE_CLICK_TIME'],gui_properties['TOOLBOX_COLOR'],gui_properties['TOOLBOX_HEIGHT'],gui_properties['TOOLBOX_WIDTH'],gui_properties['COLOR_BOX_COLORS'],gui_properties['COLOR_BOX_RECT_TUPLES']
    SELECTED_COLOR_INDEX_SINGLE_CLICK,SELECTED_COLOR_INDEX_DOUBLE_CLICK,SELECTED_COLOR,SMOKE_COLOR = gui_properties['SELECTED_COLOR_INDEX_SINGLE_CLICK'],gui_properties['SELECTED_COLOR_INDEX_DOUBLE_CLICK'],gui_properties['SELECTED_COLOR'],gui_properties['SMOKE_COLOR']
    PYGAME_ELEMENTS,COLOR_BOX_EVENT = gui_properties['PYGAME_ELEMENTS'],gui_properties['COLOR_BOX_EVENT']


    TE['clear_clickable'] = thorpy.make_button("Clear", func=clear_data)
    TE['exit_clickable'] = thorpy.make_button("Exit", func=thorpy.functions.quit_func)
    TE['vel_clickable'] = thorpy.make_button("Show Velocity", func=None)
    if webbrowser_available:
        TE['help_clickable'] = thorpy.make_button("Help", func=None)
        TE['help_clickable'].set_size((TOOLBOX_WIDTH-10,40))
    TE['viscosity_slider'] = thorpy.SliderX(length=123, limvals=(0, 999), text="Visc:", type_=int)
    TE['force_slider'] = thorpy.SliderX(length=120, limvals=(0, 999), text="Force:", type_=int)
    TE['buoyancy_text'] = thorpy.OneLineText(text="Buoyant Force:", elements=None)
    TE['buoyancy_text'].set_font_size(16)
    TE['red_buoyancy_slider'] = thorpy.SliderX(length=126, limvals=(-300, 300), text="Red:", type_=int)
    TE['green_buoyancy_slider'] = thorpy.SliderX(length=116, limvals=(-300, 300), text="Green:", type_=int)
    TE['blue_buoyancy_slider'] = thorpy.SliderX(length=125, limvals=(-300, 300), text="Blue:", type_=int)
    TE['dissipation_text'] = thorpy.OneLineText(text="Dissipation:", elements=None)
    TE['dissipation_text'].set_font_size(16)
    TE['red_dissipation_slider'] = thorpy.SliderX(length=127, limvals=(0, 1.5), text="Red:", type_=float)
    TE['green_dissipation_slider'] = thorpy.SliderX(length=120, limvals=(0, 1.5), text="Green:", type_=float)
    TE['blue_dissipation_slider'] = thorpy.SliderX(length=127, limvals=(0, 1.5), text="Blue:", type_=float)
    TE['force_slider'].set_value(simulation_properties['force']*50)
    TE['viscosity_slider'].set_value(gui_properties['VISC_SLIDER_VALUE'])
    TE['red_buoyancy_slider'].set_value(simulation_properties['temp_source_red'])
    TE['green_buoyancy_slider'].set_value(simulation_properties['temp_source_green'])
    TE['blue_buoyancy_slider'].set_value(simulation_properties['temp_source_blue'])
    TE['red_dissipation_slider'].set_value(simulation_properties['smoke_diff_away_red'])
    TE['green_dissipation_slider'].set_value(simulation_properties['smoke_diff_away_green'])
    TE['blue_dissipation_slider'].set_value(simulation_properties['smoke_diff_away_blue'])
    TE['cs'] = thorpy.ColorSetter("Choose a color", value=COLOR_BOX_COLORS[SELECTED_COLOR_INDEX_DOUBLE_CLICK])
    TE['cs'].set_size((TOOLBOX_WIDTH-10,135))
    TE['clear_clickable'].set_size((TOOLBOX_WIDTH-10,40))
    TE['exit_clickable'].set_size((TOOLBOX_WIDTH-10,40))
    TE['vel_clickable'].set_size((TOOLBOX_WIDTH-10,40))




    TE['cs_clickable'] = thorpy.make_button("Set Color")
    TE['cs_clickable'].set_size((TOOLBOX_WIDTH-10,40))

    elements = [TE['cs'],TE['cs_clickable'],TE['vel_clickable'],TE['viscosity_slider'],TE['force_slider'],TE['buoyancy_text'],TE['red_buoyancy_slider'],TE['green_buoyancy_slider'],TE['blue_buoyancy_slider'],TE['dissipation_text'],    TE['red_dissipation_slider'],    TE['green_dissipation_slider'],    TE['blue_dissipation_slider'],TE['clear_clickable'],TE['exit_clickable'],TE['help_clickable']]
    TE['central_box'] = thorpy.Box(elements=elements)
    central_box_color = tuple(list(TOOLBOX_COLOR)+[255]) #need to add an alpha value
    TE['central_box'].set_main_color(central_box_color) #set box color and opacity
    TE['menu'] = thorpy.Menu(TE['central_box'])
    for element in TE['menu'].get_population():
        element.surface = gui_properties['SCREEN']


    TE['central_box'].set_topleft((0,53))
    TE['central_box'].set_size((TOOLBOX_WIDTH,TOOLBOX_HEIGHT+70))

    TE['central_box'].blit()
    TE['central_box'].update()


def pygame_init_function():

    pygame_interface()
    make_thorpy_interface()


def pygame_idle_function():

    for geo_type,geo_list in gui_properties['PYGAME_ELEMENTS'].items():
        if geo_type == 'rect':
            for geo_instance in geo_list:
                pygame.draw.rect(gui_properties['SCREEN'],geo_instance['color'],geo_instance['rect'])
        if geo_type.find('line') > -1:
            for geo_instance in geo_list:
                pygame.draw.line(gui_properties['SCREEN'], geo_instance['color'], geo_instance['start'], geo_instance['end'], geo_instance['width'])
    pygame.display.update()
    gui_properties['THORPY_ELEMENTS']['central_box'].update()

    #clicking a color box (single click)
    if gui_properties['COLOR_BOX_EVENT']:
        tick = pygame.time.get_ticks()
        if tick >= gui_properties['COLOR_BOX_EVENT']['time'] + gui_properties['DOUBLE_CLICK_TIME']:
            gui_properties['SELECTED_COLOR_INDEX_SINGLE_CLICK'] = gui_properties['COLOR_BOX_RECT_TUPLES'].index(gui_properties['COLOR_BOX_EVENT']['rect'])
            gui_properties['SMOKE_COLOR'] = gui_properties['COLOR_BOX_COLORS'][gui_properties['SELECTED_COLOR_INDEX_SINGLE_CLICK']]
            gui_properties['COLOR_BOX_EVENT'] = None

    for event in pygame.event.get():

        gui_properties['VISC_SLIDER_VALUE'] = gui_properties['THORPY_ELEMENTS']['viscosity_slider'].get_value()
        simulation_properties['visc'] = (np.exp(gui_properties['VISC_SLIDER_VALUE']/100)-1)/(np.exp(10)*70)
        simulation_properties['force'] = gui_properties['THORPY_ELEMENTS']['force_slider'].get_value()/50
        simulation_properties['temp_source_red'] = gui_properties['THORPY_ELEMENTS']['red_buoyancy_slider'].get_value()
        simulation_properties['temp_source_green'] = gui_properties['THORPY_ELEMENTS']['green_buoyancy_slider'].get_value()
        simulation_properties['temp_source_blue'] = gui_properties['THORPY_ELEMENTS']['blue_buoyancy_slider'].get_value()
        simulation_properties['smoke_diff_away_red'] = gui_properties['THORPY_ELEMENTS']['red_dissipation_slider'].get_value()
        simulation_properties['smoke_diff_away_green'] = gui_properties['THORPY_ELEMENTS']['green_dissipation_slider'].get_value()
        simulation_properties['smoke_diff_away_blue'] = gui_properties['THORPY_ELEMENTS']['blue_dissipation_slider'].get_value()

        gui_properties['THORPY_ELEMENTS']['menu'].react(event) #thorpy events

        #clicking a color box (double click)
        if event.type == 5:
            for i,rect in enumerate(gui_properties['COLOR_BOX_RECT_TUPLES']):
                if within_rect(event.dict['pos'],rect):
                    tick = pygame.time.get_ticks()
                    if gui_properties['COLOR_BOX_EVENT'] and gui_properties['COLOR_BOX_EVENT']['rect'] == rect and gui_properties['COLOR_BOX_EVENT']['time'] > tick - gui_properties['DOUBLE_CLICK_TIME']:

                        gui_properties['SELECTED_COLOR_INDEX_DOUBLE_CLICK'] = i
                        gui_properties['SELECTED_COLOR'] = gui_properties['COLOR_BOX_COLORS'][i]


                        color_box_outline(gui_properties['SCREEN'],gui_properties['COLOR_BOX_RECT_TUPLES'][gui_properties['SELECTED_COLOR_INDEX_DOUBLE_CLICK']])
                        gui_properties['COLOR_BOX_EVENT'] = None
                        gui_properties['THORPY_ELEMENTS']['cs'].set_value(gui_properties['SELECTED_COLOR'])
                        gui_properties['THORPY_ELEMENTS']['central_box'].blit()
                        gui_properties['THORPY_ELEMENTS']['central_box'].update()

                    else:
                        gui_properties['COLOR_BOX_EVENT'] = {'time':tick,'rect':rect}

        # clicking a clickable
        if event.type == 24 and event.dict['id'] == 2: # 2 is down click
            if event.dict['el'] == gui_properties['THORPY_ELEMENTS']['cs_clickable']:
                gui_properties['COLOR_BOX_COLORS'][gui_properties['SELECTED_COLOR_INDEX_DOUBLE_CLICK']] = gui_properties['THORPY_ELEMENTS']['cs'].get_color()
                if gui_properties['SELECTED_COLOR_INDEX_DOUBLE_CLICK'] == gui_properties['SELECTED_COLOR_INDEX_SINGLE_CLICK']: # we also have to update the smoke color
                    gui_properties['SMOKE_COLOR'] = gui_properties['COLOR_BOX_COLORS'][gui_properties['SELECTED_COLOR_INDEX_SINGLE_CLICK']]
                bottom_screen_rectangle()
                add_color_boxes()
                color_box_outline(gui_properties['SCREEN'],gui_properties['COLOR_BOX_RECT_TUPLES'][gui_properties['SELECTED_COLOR_INDEX_DOUBLE_CLICK']])
            if event.dict['el'] == gui_properties['THORPY_ELEMENTS']['help_clickable']:
                webbrowser.open('help.html', new=2)
            if event.dict['el'] == gui_properties['THORPY_ELEMENTS']['vel_clickable']:
                gui_properties['DISPLAY_VELOCITY'] = not gui_properties['DISPLAY_VELOCITY']
                if gui_properties['DISPLAY_VELOCITY']:
                    gui_properties['THORPY_ELEMENTS']['vel_clickable'].set_text("Show Smoke Density")
                else:
                    gui_properties['THORPY_ELEMENTS']['vel_clickable'].set_text("Show Velocity")


        if event.type == pygame.QUIT:
            exit()

# clears velocity/density/temp data to "restart" simulation
def clear_data():

    simulation_data['u'][:] = 0.0
    simulation_data['v'][:] = 0.0
    simulation_data['u_prev'][:]= 0.0
    simulation_data['v_prev'][:]= 0.0
    simulation_data['dens'][:]= 0.0
    simulation_data['dens_prev'][:]= 0.0
    simulation_data['red_dens'][:] = 0.0
    simulation_data['red_dens_prev'][:] = 0.0
    simulation_data['green_dens'][:] = 0.0
    simulation_data['green_dens_prev'][:] = 0.0
    simulation_data['blue_dens'][:] = 0.0
    simulation_data['blue_dens_prev'][:] = 0.0
    simulation_data['temp'][:] = 0.0
    simulation_data['temp_prev'][:] = 0.0


def pre_display():

    glViewport(0, 0, gui_properties['SCREEN_WIDTH'], gui_properties['SCREEN_HEIGHT'])
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluOrtho2D(0.0, 1.0, 0.0, 1.0)
    glClearColor(0.0, 0.0, 0.0, 1.0)
    glClear(GL_COLOR_BUFFER_BIT)



def post_display():

    glutSwapBuffers()




def draw_velocity():

    N = simulation_properties['N']
    h = 1.0 / N
    SMOKE_COLOR = gui_properties['SMOKE_COLOR']

    glColor3f(1.0, 1.0, 1.0)
    glLineWidth(1.0)

    glBegin(GL_LINES)
    for i in range(1, N + 1):
        x = (i - 0.5) * h
        for j in range(1, N + 1):
            y = (j - 0.5) * h
            glColor3f(SMOKE_COLOR[0]/255, SMOKE_COLOR[1]/255, SMOKE_COLOR[2]/255)
            glVertex2f(x, y)
            glVertex2f(x + simulation_data['u'][i, j], y + simulation_data['v'][i, j])
    glEnd()


def draw_density():

    N = simulation_properties['N']
    h = 1.0 / N
    SMOKE_COLOR = gui_properties['SMOKE_COLOR']

    glBegin(GL_QUADS)
    for i in range(0, N + 1):
        x = (i - 0.5) * h
        for j in range(0, N + 1):
            y = (j - 0.5) * h
            d1_00 = min(simulation_data['red_dens'][i, j],1)
            d1_01 = min(simulation_data['red_dens'][i, j + 1],1)
            d1_10 = min(simulation_data['red_dens'][i + 1, j],1)
            d1_11 = min(simulation_data['red_dens'][i + 1, j + 1],1)
            d2_00 = min(simulation_data['green_dens'][i, j],1)
            d2_01 = min(simulation_data['green_dens'][i, j + 1],1)
            d2_10 = min(simulation_data['green_dens'][i + 1, j],1)
            d2_11 = min(simulation_data['green_dens'][i + 1, j + 1],1)
            d3_00 = min(simulation_data['blue_dens'][i, j],1)
            d3_01 = min(simulation_data['blue_dens'][i, j + 1],1)
            d3_10 = min(simulation_data['blue_dens'][i + 1, j],1)
            d3_11 = min(simulation_data['blue_dens'][i + 1, j + 1],1)

            glColor3f(d1_00, d2_00, d3_00)
            glVertex2f(x, y)
            glColor3f(d1_10, d2_10, d3_10)
            glVertex2f(x + h, y)
            glColor3f(d1_11, d2_11, d3_11)
            glVertex2f(x + h, y + h)
            glColor3f(d1_01, d2_01, d3_01)
            glVertex2f(x, y + h)
    glEnd()




def get_from_UI():
    N = simulation_properties['N']

    simulation_data['dens_prev'][:] = 0.0
    simulation_data['red_dens_prev'][:] = 0.0
    simulation_data['green_dens_prev'][:] = 0.0
    simulation_data['blue_dens_prev'][:] = 0.0
    simulation_data['u_prev'][:] = 0.0
    simulation_data['v_prev'][:] = 0.0
    simulation_data['temp_prev'][:] = 0.0


    if not gui_properties['MOUSE_DOWN'][GLUT_LEFT_BUTTON] and not gui_properties['MOUSE_DOWN'][GLUT_RIGHT_BUTTON]:
        return

    i = int((gui_properties['MOUSE_X'] / float(gui_properties['SCREEN_WIDTH'])) * N + 1)
    j = int(((gui_properties['SCREEN_HEIGHT'] - float(gui_properties['MOUSE_Y'])) / float(gui_properties['SCREEN_HEIGHT'])) * float(N) + 1.0)

    if i < 1 or i > N or j < 1 or j > N:
        return

    if gui_properties['MOUSE_DOWN'][GLUT_LEFT_BUTTON]:
        simulation_data['u_prev'][i, j] = 0.5*simulation_properties['force'] * (gui_properties['MOUSE_X'] - gui_properties['ORIG_MOUSE_X']) #for staggered grid, we add half of velocity to each of the surrounding faces
        simulation_data['u_prev'][i+1,j] = 0.5*simulation_properties['force'] * (gui_properties['MOUSE_X'] - gui_properties['ORIG_MOUSE_X'])

        simulation_data['v_prev'][i, j] = 0.5*simulation_properties['force'] * (gui_properties['ORIG_MOUSE_Y'] - gui_properties['MOUSE_Y'])
        simulation_data['v_prev'][i, j+1] = 0.5*simulation_properties['force'] * (gui_properties['ORIG_MOUSE_Y'] - gui_properties['MOUSE_Y'])

    elif gui_properties['MOUSE_DOWN'][GLUT_RIGHT_BUTTON]:
        simulation_data['red_dens_prev'][i, j] = simulation_properties['dens_source']*gui_properties['SMOKE_COLOR'][0]/255
        simulation_data['green_dens_prev'][i, j] = simulation_properties['dens_source']*gui_properties['SMOKE_COLOR'][1]/255
        simulation_data['blue_dens_prev'][i, j] = simulation_properties['dens_source']*gui_properties['SMOKE_COLOR'][2]/255
        simulation_data['temp_prev'][ i, j] = simulation_properties['temp_source_red']*gui_properties['SMOKE_COLOR'][0]/255 +simulation_properties['temp_source_green']*gui_properties['SMOKE_COLOR'][1]/255 + simulation_properties['temp_source_blue']*gui_properties['SMOKE_COLOR'][2]/255
    gui_properties['ORIG_MOUSE_X'] = gui_properties['MOUSE_X']
    gui_properties['ORIG_MOUSE_Y'] = gui_properties['MOUSE_Y']


def key_func(key, x, y):

    if key == b'c' or key == b'C':
        clear_data()
    if key == b'v' or key == b'V':
        gui_properties['DISPLAY_VELOCITY'] = not gui_properties['DISPLAY_VELOCITY']
    if key == b'\x1b':
        exit()
    if key == b'r' or key == b'R':
        gui_properties['SMOKE_COLOR'] = (255,0,0)
    if key == b'g' or key == b'G':
        gui_properties['SMOKE_COLOR'] = (0,255,0)
    if key == b'b' or key == b'B':
        gui_properties['SMOKE_COLOR'] = (0,0,255)
    if key == b'w' or key == b'W':
        gui_properties['SMOKE_COLOR'] = (255,255,255)


def mouse_func(button, state, x, y):

    gui_properties['MOUSE_X'] = x
    gui_properties['ORIG_MOUSE_X'] = x
    gui_properties['MOUSE_Y'] = y
    gui_properties['ORIG_MOUSE_Y'] = y

    gui_properties['MOUSE_DOWN'][button] = (state == GLUT_DOWN)

def motion_func(x, y):

    gui_properties['MOUSE_X'] = x
    gui_properties['MOUSE_Y'] = y



def reshape_func(width, height):

    glutReshapeWindow(width, height)
    gui_properties['SCREEN_WIDTH'] = width
    gui_properties['SCREEN_HEIGHT'] = height

# GLUT idle function
def idle_func():

    N, visc, dt, diff, menu = simulation_properties['N'], simulation_properties['visc'], simulation_properties['dt'], ['diff'], gui_properties['THORPY_ELEMENTS']['menu']
    simulation_properties['dt'] = gui_properties['CLOCK'].tick()/1000

    get_from_UI()


    dens_step()
    velocity_step()

    glutPostRedisplay()
    pygame_idle_function()

def display_func():

    pre_display()
    if gui_properties['DISPLAY_VELOCITY']:
        draw_velocity()
    else:
        draw_density()
    post_display()

def open_glut_window():


    glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE)
    glutInitWindowPosition(80, 100)
    glutInitWindowSize(gui_properties['SCREEN_WIDTH'], gui_properties['SCREEN_HEIGHT'])
    glutCreateWindow("Fluid Solver with Staggered Grid")
    glClearColor(0.0, 0.0, 0.0, 1.0)
    glClear(GL_COLOR_BUFFER_BIT)
    glutSwapBuffers()
    glClear(GL_COLOR_BUFFER_BIT)
    glutSwapBuffers()

    pre_display()
    pygame_init_function()

    glutKeyboardFunc(key_func)
    glutMouseFunc(mouse_func)
    glutMotionFunc(motion_func)
    glutReshapeFunc(reshape_func)
    glutIdleFunc(idle_func)
    glutDisplayFunc(display_func)


def dens_step():
    add_source(simulation_data['temp'],simulation_data['temp_prev'])
    add_source(simulation_data['red_dens'],simulation_data['red_dens_prev'])
    add_source(simulation_data['green_dens'],simulation_data['green_dens_prev'])
    add_source(simulation_data['blue_dens'],simulation_data['blue_dens_prev'])
    simulation_data['temp'],simulation_data['temp_prev'] = simulation_data['temp_prev'],simulation_data['temp'] # swap
    simulation_data['red_dens'],simulation_data['red_dens_prev'] = simulation_data['red_dens_prev'],simulation_data['red_dens']
    simulation_data['green_dens'],simulation_data['green_dens_prev'] = simulation_data['green_dens_prev'],simulation_data['green_dens']
    simulation_data['blue_dens'],simulation_data['blue_dens_prev'] = simulation_data['blue_dens_prev'],simulation_data['blue_dens']
    diffuse(simulation_data['temp'],simulation_data['temp_prev'],0,simulation_properties['temp_diff'])
    diffuse(simulation_data['red_dens'],simulation_data['red_dens_prev'],0,simulation_properties['diff'])
    diffuse(simulation_data['green_dens'],simulation_data['green_dens_prev'],0,simulation_properties['diff'])
    diffuse(simulation_data['blue_dens'],simulation_data['blue_dens_prev'],0,simulation_properties['diff'])
    simulation_data['temp'],simulation_data['temp_prev'] = simulation_data['temp_prev'],simulation_data['temp'] # swap
    simulation_data['red_dens'],simulation_data['red_dens_prev'] = simulation_data['red_dens_prev'],simulation_data['red_dens']
    simulation_data['green_dens'],simulation_data['green_dens_prev'] = simulation_data['green_dens_prev'],simulation_data['green_dens']
    simulation_data['blue_dens'],simulation_data['blue_dens_prev'] = simulation_data['blue_dens_prev'],simulation_data['blue_dens']
    advect(simulation_data['temp'],simulation_data['temp_prev'],simulation_data['u'],simulation_data['v'],0)
    advect(simulation_data['red_dens'],simulation_data['red_dens_prev'],simulation_data['u'],simulation_data['v'],0)
    advect(simulation_data['green_dens'],simulation_data['green_dens_prev'],simulation_data['u'],simulation_data['v'],0)
    advect(simulation_data['blue_dens'],simulation_data['blue_dens_prev'],simulation_data['u'],simulation_data['v'],0)
    diffuse_away(simulation_data['temp'],simulation_properties['temp_diff_away'])
    diffuse_away(simulation_data['red_dens'],simulation_properties['smoke_diff_away_red'])
    diffuse_away(simulation_data['green_dens'],simulation_properties['smoke_diff_away_green'])
    diffuse_away(simulation_data['blue_dens'],simulation_properties['smoke_diff_away_blue'])


# just a way to have smoke density reduce over time in each cell for better visuals
# also used to have localized temperature hot spots reduce over time
def diffuse_away(m,coeff):
    m[0:size,0:size] = coeff*m[0:size,0:size]

def velocity_step():

    #u_prev and v_prev used as source velocities at the start of velocity_step() routine
    for char in ['u','v']:
        add_source(simulation_data[char],simulation_data[char+'_prev'],vel=True)
        simulation_data[char],simulation_data[char+'_prev'] = simulation_data[char+'_prev'],simulation_data[char] # swap
        diffuse(simulation_data[char],simulation_data[char+'_prev'],1+(char=='v'),simulation_properties['visc']) # viscous diffusion. b==1 for 'u', b==2 for 'v'

    project()
    for char in ['u','v']:
        simulation_data[char],simulation_data[char+'_prev'] = simulation_data[char+'_prev'],simulation_data[char] # swap
    for i,char in enumerate(['u','v']):
        advect(simulation_data[char],simulation_data[char+'_prev'],simulation_data['u_prev'],simulation_data['v_prev'],i+1)
    project()

    apply_buoyant_force()
    apply_vorticity_confinement()
    project()


# adds the pseudoforce based on vorticity confinement to the velocity matrices
# this uses the u_prev and v_prev matrices which are no longer needed when this function is called in the velocity step
def apply_vorticity_confinement():
    X = simulation_data['u']
    Y = simulation_data['v']
    N = simulation_properties['N']
    dt = simulation_properties['dt']
    size = simulation_properties['size']
    epsilon = simulation_properties['vorticity_confinement_constant']
    mag_curl = np.absolute(curl2D(X,Y))
    eta = np.gradient(mag_curl)
    delta = (10**-20)/(1.0/N)/dt #prevent divide by zero errors
    for i in range(N):
        for j in range(N):
            mag = np.sqrt(eta[0][j,i]**2 + eta[1][j,i]**2) + delta
            eta[0][j,i] /= mag
            eta[1][j,i] /= mag
    capitalN = eta
    curl_array = np.array([np.zeros(shape=(N+2,N+2)),np.zeros(shape=(N+2,N+2)),curl2D(X,Y)])
    vct =  (1.0/N)*epsilon*np.cross(capitalN,curl_array,axisa=0,axisb=0,axisc=0)

    simulation_data['u'][0:size,0:size] += dt*0.5*vct[0][0:size,0:size]
    simulation_data['u'][1:size+1,0:size] += dt*0.5*vct[0][0:size,0:size]
    simulation_data['v'][0:size,0:size] += dt*0.5*vct[1][0:size,0:size]
    simulation_data['v'][1:size+1,0:size] += dt*0.5*vct[1][0:size,0:size]





# calculates the scalar field curl based on u- and v- velocity matrices given as X and Y respectively
# note this function returns a scalar field with a different size as X and Y (N+2 instead of N+3)
# again, note this function returns something. Essentially nothing else in this program has a return value
def curl2D(X,Y):
    N = simulation_properties['N']
    h = 1.0/N

    dXdy = np.zeros(shape=(N+2,N+2), dtype=(np.float64))
    dXdy[1:N+1,0:N+2] = (X[2:N+2,0:N+2] - X[0:N,0:N+2])/(2*h)
    dXdy[0,0:N+2] = (X[1,0:N+2] - X[0,0:N+2])/h
    dXdy[N+1,0:N+2] = (X[N+1,0:N+2] - X[N,0:N+2])/h

    dYdx = np.zeros(shape=(N+2,N+2), dtype=(np.float64))
    dYdx[0:N+2,1:N+1] = (Y[0:N+2,2:N+2] - Y[0:N+2,0:N])/(2*h)
    dYdx[0:N+2,0] = (Y[0:N+2,1] - Y[0:N+2,0])/h
    dYdx[0:N+2,N+1] = (Y[0:N+2,N+1] - Y[0:N+2,N])/h

    return dYdx - dXdy


# adds an upward velocity to regions with smoke density to simulate the effects of buoyancy
# due to density differences at different temperatures
#TODO: make this actually depend on temperature
def apply_buoyant_force():
    bc = simulation_properties['buoyancy']
    dt = simulation_properties['dt']
    size = simulation_properties['size']
    simulation_data['v'][0:size,0:size] += 0.5*bc*dt*simulation_data['temp'][0:size,0:size]
    simulation_data['v'][1:size+1,0:size] += 0.5*bc*dt*simulation_data['temp'][0:size,0:size]

# advects the velocity according to a linear backtrace
# requires prev velocity from both u- and v- velocity demonsions
# but only updates one velocity dimension at a time (given as m)
# advect(simulation_data['u'],simulation_data[char+'_prev'],0+1)
def advect(m,m0,u,v,b):
    N = simulation_properties['N']
    dt0 = simulation_properties['dt'] * N
    for i in range(1, N + 1):
        for j in range(1, N + 1):
            x = i - dt0 * (u[i, j]+u[i+1,j])/2
            y = j - dt0 * (v[i, j]+v[i,j+1])/2
            if x < 0.5:
                x = 0.5
            if x > N + 0.5:
                x = N + 0.5
            i0 = int(x)
            i1 = i0 + 1
            if y < 0.5:
                y = 0.5
            if y > N + 0.5:
                y = N + 0.5
            j0 = int(y)
            j1 = j0 + 1
            s1 = x - i0
            s0 = 1 - s1
            t1 = y - j0
            t0 = 1 - t1
            m[i, j] = (s0 * (t0 * m0[i0, j0] + t1 * m0[i0, j1]) + s1 *
                       (t0 * m0[i1, j0] + t1 * m0[i1, j1]))
    set_bnd(b,m)



def project():
    # the u_prev and v_prev are unneeded at the time of project() and are used as
    # the irrotational and solenoidal fields in itteratively solving the Helmholtz decomposition
    p = simulation_data['u_prev']
    div = simulation_data['v_prev']
    N = simulation_properties['N']
    h = 1.0 / N # inter-grid spacing
    div[1:N+2,1:N+2] = (-0.5 * h *
                       (simulation_data['u'][2:N + 3, 1:N + 2] - simulation_data['u'][0:N+1, 1:N + 2] +
                        simulation_data['v'][1:N + 2, 2:N + 3] - simulation_data['v'][1:N + 2, 0:N+1]))  #divergence
    p[1:N+2,1:N+2] = 0 # divergence-free
    set_bnd(0,div)
    set_bnd(0,p)
    lin_solve(p,div,1,4,b=0)
    simulation_data['u'][1:N+1,1:N+1] -= 0.5 * (p[2:N+2,1:N+1] - p[0:N,1:N+1]) / h
    simulation_data['v'][1:N+1,1:N+1] -= 0.5 * (p[1:N+1,2:N+2] - p[1:N+1,0:N]) / h
    for i,char in enumerate(['u','v']):
        set_bnd(i+1,simulation_data[char],vd=char)

# adds velocity in one dimension
# presumably this is used twice (x- and y-)
# m is the u- or v- velocities in the simulation_data
# s is a matrix of forces such as from user input
# vel=True for a velocity matrix
def add_source(m,s,vel=False):
    size = simulation_properties['size']
    dt = simulation_properties['dt']
    m[0:size+1+vel,0:size+1+vel] += (dt if vel else 1) * s[0:size+1+vel,0:size+1+vel]


# diffuses smoke density
# also used for velocities as "viscous diffusion"
def diffuse(m,m0,b,coeff,vd=None):
    a = simulation_properties['dt'] * coeff * \
        simulation_properties['N']**2
    lin_solve(m,m0,a,1+4*a,b=b,vd=vd)


# linear solver using Gauss-Seidel relaxation
# bounds differ for velocity solvers
# m is the matrix to solve for and m0 is the old matrix
# b is for setting bounds (according to numerical code in Stam paper)
# vd is velcity dimension. Use 'u' or 'v' or None if not solving velocities
# the function will break if both vd and b are None
def lin_solve(m, m0, a, c, b=None, vd=None):
    N = simulation_properties['N']
    kf = simulation_properties['linear_solver_tries']
    if vd == 'u':
        b = 1
    elif vd == 'v':
        b = 2
    for k in range(0, kf):
        m[1:N+1+(vd=='u'),1:N+1+(vd=='v')] = (m0[1:N+1+(vd=='u'),1:N+1+(vd=='v')] + a *
                                              (m[0:N+(vd=='u'),1:N+1+(vd=='v')] +
                                               m[2:N+2+(vd=='u'),1:N+1+(vd=='v')] +
                                               m[1:N+1+(vd=='u'),0:N+(vd=='v')] +
                                               m[1:N+1+(vd=='u'),2:N+2+(vd=='v')])) / c
        set_bnd(b,m)
    # i use they same b-codes for dimension properties for the set_bnd rountine as in the original paper
    # however they do not need to be explicility provided if the function knows this is a lin_solve
    # for velocitiy because the dimension is specified



# sets the boundaries of the simulation
# slightly different calculations occur for velocity matrices
# depending on the dimension (u- or v-) because of the mismatched sizes in the
# staggered grid
# TODO: del this line           for i,char in enumerate(['u']):
        #set_bnd(i+1,simulation_data[char],vd=char)
def set_bnd(b,m,vd=None):
    N = simulation_properties['N']

    # setting bounds on edges
    # note that velocity grids are still square-shaped, so this routine ends up doing
    # calculations on a unused extraneous row of data for velocity-grids as an ease-of-programming trade-off
    for i in range(1, N + 1 + 0):
        if b == 1:
            m[0, i] = -m[1, i]
        else:
            m[0, i] = m[1, i]
        if b == 1:
            m[N + 1 + (vd=='u'), i] = -m[N + (vd=='u'), i]
        else:
            m[N + 1 + (vd=='u'), i] = m[N + (vd=='u'), i]
        if b == 2:
            m[i, 0] = -m[i, 1]
        else:
            m[i, 0] = m[i, 1]
        if b == 2:
            m[i, N + 1 + (vd=='v')] = -m[i, N + (vd=='v')]
        else:
            m[i, N + 1 + (vd=='v')] = m[i, N + (vd=='v')]

    if vd=='u':
       i = N+1
       if b == 2:
           m[i, 0] = -m[i, 1]
       else:
           m[i, 0] = m[i, 1]
       if b == 2:
          m[i, N + 1] = -m[i, N]
       else:
         m[i, N + 1] = m[i, N]
    elif vd=='v':
       i = N+1
       if b == 1:
         m[0, i] = -m[1, i]
       else:
         m[0, i] = m[1, i]
       if b == 1:
         m[N + 1, i] = -m[N, i]
       else:
         m[N + 1, i] = m[N, i]


    # setting bounds on corners
    m[0, 0] = 0.5 * (m[1, 0] + m[0, 1])
    m[0, N + 1 + (vd=='v')] = 0.5 * (m[1, N + 1 + (vd=='v')] + m[0, N + (vd=='v')])
    m[N + 1 + (vd=='u'), 0] = 0.5 * (m[N + (vd=='u'), 0] + m[N + 1 + (vd=='u'), 1])
    m[N + 1 + (vd=='u'), N + 1 + (vd=='v')] = 0.5 * (m[N + (vd=='u'), N + 1 + (vd=='v')] + m[N + 1 + (vd=='u'), N + (vd=='v')])

def main():

    glutInit()
    clear_data()
    open_glut_window()
    glutMainLoop()



if __name__ == '__main__':

    main()
