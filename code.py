import time
import random
from random import randrange
import board
import busio
import neopixel
import displayio
from adafruit_gizmo import tft_gizmo
import adafruit_imageload
import adafruit_lis3dh

from adafruit_bluefruit_connect.packet import Packet
from adafruit_bluefruit_connect.color_packet import ColorPacket
from adafruit_bluefruit_connect.button_packet import ButtonPacket


from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService


#===| User Config |==================================================
SNOWGLOBE_NAME = "SNOWGLOBE" # name that will show up on smart device
DEFAULT_ANIMATION = 0        # 0-3, index in ANIMATIONS list
DEFAULT_DURATION = 5         # total seconds to play animation
DEFAULT_SPEED = 0.1          # delay in seconds between updates
DEFAULT_COLOR = 0xFF0000     # hex color value
DEFAULT_SHAKE = 20           # lower number is more sensitive
# you can define more animation functions below
# here, specify the four to be used
ANIMATIONS = ('spin', 'pulse', 'strobe', 'sparkle')
#===| User Config |==================================================

# Configuration settings
snow_config = {
    'animation' : DEFAULT_ANIMATION,
    'duration' : DEFAULT_DURATION,
    'speed' : DEFAULT_SPEED,
    'color' : DEFAULT_COLOR,
    'shake' : DEFAULT_SHAKE,
}

# Setup NeoPixels
pixels = neopixel.NeoPixel(board.NEOPIXEL, 10)

# Setup accelo
accelo_i2c = busio.I2C(board.ACCELEROMETER_SCL, board.ACCELEROMETER_SDA)
accelo = adafruit_lis3dh.LIS3DH_I2C(accelo_i2c, address=0x19)

# Setup BLE
ble = BLERadio()
uart = UARTService()
advertisement = ProvideServicesAdvertisement(uart)
ble._adapter.name = SNOWGLOBE_NAME #pylint: disable=protected-access

#--| ANIMATIONS |----------------------------------------------------
def spin(config):
    start_time = time.monotonic()
    last_update = start_time
    p = -1
    while time.monotonic() - start_time < config['duration']:
        if time.monotonic() - last_update > config['speed']:
            pixels.fill(0)
            pixels[p % 10] = pick_color(p % 10)
            p -= 1
            last_update = time.monotonic()

def pixels_fill():
    for i in range(10):
        pixels[i] = pick_color(i)

def pulse(config):
    start_time = time.monotonic()
    last_update = start_time
    brightness = 0
    delta = 0.05
    pixels.brightness = 0
    pixels_fill()
    while time.monotonic() - start_time < config['duration']:
        if time.monotonic() - last_update > config['speed']:
            brightness += delta
            if brightness > 1:
                brightness = 1
                delta *= -1
            if brightness < 0:
                brightness = 0
                delta *= -1
            pixels.brightness = brightness
            last_update = time.monotonic()

def strobe(config):
    start_time = time.monotonic()
    last_update = start_time
    turn_on = True
    while time.monotonic() - start_time < config['duration']:
        if time.monotonic() - last_update > config['speed']:
            if turn_on:
                pixels_fill()
            else:
                pixels.fill(0)
            turn_on = not turn_on
            last_update = time.monotonic()

def sparkle(config):
    start_time = time.monotonic()
    last_update = start_time
    while time.monotonic() - start_time < config['duration']:
        if time.monotonic() - last_update > config['speed']:
            pixels.fill(0)
            pixels[random.randint(0, 9)] = pick_color(random.randint(0,1))
            last_update = time.monotonic()
#--| ANIMATIONS |----------------------------------------------------

def play_animation(config):
    #pylint: disable=eval-used
    eval(ANIMATIONS[config['animation']])(config)
    pixels.fill(0)

def pick_color(i):

   if i%2:
       return snow_config['color']
   else:
       return (~snow_config['color']) & 0xFFFFFF

def indicate(event=None):
    if not isinstance(event, str):
        return
    event = event.strip().upper()
    if event == 'START':
        for _ in range(2):
            for i in range(10):
                pixels[i] = pick_color(i)
                time.sleep(0.05)
                pixels.fill(0)
    if event == 'CONNECTED':
        for _ in range(5):
            pixels.fill(0x0000FF)
            time.sleep(0.1)
            pixels.fill(0)
            time.sleep(0.1)
    if event == 'DISCONNECTED':
        for _ in range(5):
            pixels.fill(0x00FF00)
            time.sleep(0.1)
            pixels.fill(0)
            time.sleep(0.1)

indicate('START')


# Are we already advertising?
advertising = False

#---| User Config |---------------
BACKGROUND = "/ikeAndLuke256.bmp"    # specify color or background BMP file

NUM_FLAKES = 50                    # total number of snowflakes
FLAKE_SHEET = "/flakes_sheet.bmp"  # flake sprite sheet
FLAKE_WIDTH = 4                    # sprite width
FLAKE_HEIGHT = 4                   # sprite height
FLAKE_TRAN_COLOR = 0x000000        # transparency color

SNOW_COLOR = 0xFFFFFF              # snow color

SHAKE_THRESHOLD = 27               # shake sensitivity, lower=more sensitive
#---| User Config |---------------


# Create the TFT Gizmo display
display = tft_gizmo.TFT_Gizmo()

# Load background image
try:
    bg_bitmap, bg_palette = adafruit_imageload.load(BACKGROUND,
                                                    bitmap=displayio.Bitmap,
                                                    palette=displayio.Palette)
# Or just use solid color
except (OSError, TypeError):
    BACKGROUND = BACKGROUND if isinstance(BACKGROUND, int) else 0x000000
    bg_bitmap = displayio.Bitmap(display.width, display.height, 1)
    bg_palette = displayio.Palette(1)
    bg_palette[0] = BACKGROUND
background = displayio.TileGrid(bg_bitmap, pixel_shader=bg_palette)


# Snowflake setup
flake_bitmap, flake_palette = adafruit_imageload.load(FLAKE_SHEET,
                                                      bitmap=displayio.Bitmap,
                                                      palette=displayio.Palette)
if FLAKE_TRAN_COLOR is not None:
    for i, color in enumerate(flake_palette):
        if color == FLAKE_TRAN_COLOR:
            flake_palette.make_transparent(i)
            break
NUM_SPRITES = flake_bitmap.width // FLAKE_WIDTH * flake_bitmap.height // FLAKE_HEIGHT
flake_pos = [0.0] * NUM_FLAKES
flakes = displayio.Group(max_size=NUM_FLAKES)
for _ in range(NUM_FLAKES):
    flakes.append(displayio.TileGrid(flake_bitmap, pixel_shader=flake_palette,
                                     width = 1,
                                     height = 1,
                                     tile_width = FLAKE_WIDTH,
                                     tile_height = FLAKE_HEIGHT,
                                     x = randrange(0, display.width),
                                     default_tile=randrange(0, NUM_SPRITES)))

# Snowfield setup
snow_depth = [display.height] * display.width
snow_palette = displayio.Palette(2)
snow_palette[0] = 0xADAF00   # transparent color
snow_palette[1] = SNOW_COLOR # snow color
snow_palette.make_transparent(0)
snow_bitmap = displayio.Bitmap(display.width, display.height, len(snow_palette))
snow = displayio.TileGrid(snow_bitmap, pixel_shader=snow_palette)

# Add everything to display
splash = displayio.Group()
splash.append(background)
splash.append(flakes)
splash.append(snow)
display.show(splash)

def clear_the_snow():
    #pylint: disable=global-statement, redefined-outer-name
    global flakes, flake_pos, snow_depth
    display.auto_refresh = False
    for flake in flakes:
        # set to a random sprite
        flake[0] = randrange(0, NUM_SPRITES)
        # set to a random x location
        flake.x = randrange(0, display.width)
    # set random y locations, off screen to start
    flake_pos = [-1.0*randrange(0, display.height) for _ in range(NUM_FLAKES)]
    # reset snow level
    snow_depth = [display.height] * display.width
    # and snow bitmap
    for i in range(display.width*display.height):
        snow_bitmap[i] = 0
    display.auto_refresh = True

def add_snow(index, amount, steepness=2):
    location = []
    # local steepness check
    for x in range(index - amount, index + amount):
        add = False
        if x == 0:
            # check depth to right
            if snow_depth[x+1] - snow_depth[x] < steepness:
                add = True
        elif x == display.width - 1:
            # check depth to left
            if snow_depth[x-1] - snow_depth[x] < steepness:
                add = True
        elif 0 < x < display.width - 1:
            # check depth to left AND right
            if snow_depth[x-1] - snow_depth[x] < steepness and \
               snow_depth[x+1] - snow_depth[x] < steepness:
                add = True
        if add:
            location.append(x)
    # add where snow is not too steep
    for x in location:
        new_level = snow_depth[x] - 1
        if new_level >= 0:
            snow_depth[x] = new_level
            snow_bitmap[x, new_level] = 1

def update_snowflakes():
    global flakes, flake_pos, snow_depth
    if snow_depth.count(0) >= display.width:
        clear_the_snow()

    for i, flake in enumerate(flakes):
        # speed based on sprite index
        flake_pos[i] += 1 - flake[0] / NUM_SPRITES
        # check if snowflake has hit the ground
        if flake_pos[i] >= snow_depth[flake.x]:
            # add snow where it fell
            add_snow(flake.x, FLAKE_WIDTH)
            # reset flake to top
            flake_pos[i] = 0
            # at a new x location
            flake.x = randrange(0, display.width)
        flake.y = int(flake_pos[i])
    display.refresh()

while True:

    # While BLE is *not* connected
    while not ble.connected:
        if accelo.shake(snow_config['shake'], 5, 0):
            play_animation(snow_config)
            clear_the_snow();
        if not advertising:
            ble.start_advertising(advertisement)
            advertising = True
        update_snowflakes()

    # connected
    indicate('CONNECTED')


    while ble.connected:
        # Once we're connected, we're not advertising any more.
        advertising = False

        if accelo.shake(snow_config['shake'], 5, 0):
            play_animation(snow_config)
            clear_the_snow()

        update_snowflakes()

        if uart.in_waiting:
            try:
                packet = Packet.from_stream(uart)
            except ValueError:
                continue

            if isinstance(packet, ColorPacket):
                #
                # COLOR
                #
                snow_config['color'] = packet.color[0] << 16 | packet.color[1] << 8 | packet.color[2]
                pixels.fill(snow_config['color'])
                time.sleep(0.5)
                pixels.fill(0)

            if isinstance(packet, ButtonPacket) and packet.pressed:
                #
                # SPEED
                #
                if packet.button == ButtonPacket.UP:
                    speed = snow_config['speed'] - 0.05
                    speed = 0.05 if speed < 0.05 else speed
                    snow_config['speed'] = speed
                    play_animation(snow_config)
                if packet.button == ButtonPacket.DOWN:
                    speed = snow_config['speed'] + 0.05
                    snow_config['speed'] = speed
                    play_animation(snow_config)

                #
                # DURATION
                #
                if packet.button == ButtonPacket.LEFT:
                    duration = snow_config['duration'] - 1
                    duration = 1 if duration < 1 else duration
                    snow_config['duration'] = duration
                    play_animation(snow_config)
                if packet.button == ButtonPacket.RIGHT:
                    duration = snow_config['duration'] + 1
                    snow_config['duration'] = duration
                    play_animation(snow_config)

                #
                # ANIMATION
                #
                if packet.button == ButtonPacket.BUTTON_1:
                    snow_config['animation'] = 0
                    play_animation(snow_config)
                if packet.button == ButtonPacket.BUTTON_2:
                    snow_config['animation'] = 1
                    play_animation(snow_config)
                if packet.button == ButtonPacket.BUTTON_3:
                    snow_config['animation'] = 2
                    play_animation(snow_config)
                if packet.button == ButtonPacket.BUTTON_4:
                    snow_config['animation'] = 3
                    play_animation(snow_config)

    # disconnected
    indicate('DISCONNECTED')