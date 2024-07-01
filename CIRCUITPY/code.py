import board
import busio
import digitalio
import time
import microcontroller
import os
import gc
import supervisor

try:
    from typing import Optional, Tuple, Dict, List
except ImportError:
    pass

import adafruit_requests
import adafruit_connection_manager
from adafruit_wiznet5k.adafruit_wiznet5k import WIZNET5K
from adafruit_httpserver import Server, Request, Response, Redirect

# SPI0
SPI0_SCK = board.GP18
SPI0_TX = board.GP19
SPI0_RX = board.GP16
SPI0_CSn = board.GP17

# reset
W5x00_RSTn = board.GP20

print("Wiznet5k serial web interface")

# define your own unique MAC address for the network interface
MAC_ADDR = "DE:AD:BE:EF:FE:ED"

user_led = digitalio.DigitalInOut(board.GP25)
user_led.direction = digitalio.Direction.OUTPUT

# GP4&5 is Channel1 on the Waveshare Pico-2CH-RS232
uart = busio.UART(board.GP4, board.GP5, baudrate=9600)

spi_bus = busio.SPI(SPI0_SCK, MOSI=SPI0_TX, MISO=SPI0_RX)
eth_cs = digitalio.DigitalInOut(SPI0_CSn)
eth_rst = digitalio.DigitalInOut(W5x00_RSTn)
eth_rst.direction = digitalio.Direction.OUTPUT
try:
    eth = WIZNET5K(spi_bus, eth_cs, reset=eth_rst, is_dhcp=True, mac=MAC_ADDR,
                   hostname="W5100S", debug=False)
except AssertionError:
    # DHCP can fail, rarely, which will fail an assertion and halt the program
    # https://github.com/adafruit/Adafruit_CircuitPython_Wiznet5k/issues/57
    supervisor.reload()

print("machine:", os.uname().machine)
print("sysname:", os.uname().sysname)
print("CircuitPython version:", os.uname().version)
print("Chip Version:", eth.chip)
print("MAC Address:", ":".join("%02X" % _ for _ in eth.mac_address))
print("IP Address:", eth.pretty_ip(eth.ip_address))

# Initialize a requests object with a socket and ethernet interface
pool = adafruit_connection_manager.get_radio_socketpool(eth)
ssl_context = adafruit_connection_manager.get_radio_ssl_context(eth)
requests = adafruit_requests.Session(pool, ssl_context)

# Here we create our application, registering the
# following functions to be called on specific HTTP GET requests routes
web_app = Server(pool, debug=True)


# HTTP Request handlers
@web_app.route("/led/", ["GET", "POST"])
def led(request: Request) -> Response:
    print(f"\n{request.method} {request.path}")
    set_value = None
    if request.method == "GET":
        set_value = request.query_params.get('set')
    elif request.method == "POST":
        set_value = request.form_data.get('set')
    if set_value is not None:
        if set_value == 'toggle':
            user_led.value = not user_led.value
        else:
            user_led.value = True if set_value == 'on' else False
    status = 'on' if user_led.value else 'off'
    return Response(request, body=html_doc("User LED status", f"""LED is {status}<br><br>
    <form action="/led/" method="post">
    Actions:<br>
    <input type="radio" id="on" name="set" value="on"><label for="on"> turn LED on</label><br>
    <input type="radio" id="off" name="set" value="off"><label for="off"> turn LED off</label><br>
    <input type="radio" id="toggle" name="set" value="toggle"><label for="toggle"> toggle LED state</label><br>
    <button type="submit">Submit</button>
    </form><br><br>
    <a href="/" id="root">Back to root</a>"""), content_type="text/html")


@web_app.route("/led")
def led_redirect(request: Request) -> Response:
    print(f"\nRedirect {request.path} -> /led/")
    return Redirect(request, "/led/")


def serial_commands() -> str:
    return '''Some commands to try:<br><ul>
<li><a href="/serial/RSPW1---/">/serial/RSPW1---/ - Enable power on command</a></li>
<li><a href="/serial/RSPW0---/">/serial/RSPW0---/ - Disable power on command</a></li>
<li><a href="/serial/POWR1---/">/serial/POWR1---/ - Power On</a></li>
<li><a href="/serial/POWR0---/">/serial/POWR0---/ - Power Off</a></li>
<li><a href="/serial/POWRQ---/">/serial/POWRQ---/ - Is the TV on?</a></li>
<li><a href="/serial/VOLMQQ--/">/serial/VOLMQQ--/ - What's the current volume?</a></li>
<li><a href="/serial/VOLM04--/">/serial/VOLM04--/ - Set volume to 4</a></li>
<li><a href="/serial/VOLM10--/">/serial/VOLM10--/ - Set volume to 10</a></li>
<li><a href="/serial/VOLM15--/">/serial/VOLM15--/ - Set volume to 15</a></li>
<li><a href="/serial/MUTE0---/">/serial/MUTE0---/ - Toggle Mute</a></li>
<li><a href="/serial/MUTE1---/">/serial/MUTE1---/ - Mute On</a></li>
<li><a href="/serial/MUTE2---/">/serial/MUTE2---/ - Mute Off</a></li>
<li><a href="/serial/MUTEQ---/">/serial/MUTEQ---/ - Is Mute On?</a></li>
<li><a href="/serial/ITVD0---/">/serial/ITVD0---/ - Switch input to TV</a></li>
<li><a href="/serial/IAVD1---/">/serial/IAVD1---/ - Switch input to input1</a></li>
<li><a href="/serial/IAVD7---/">/serial/IAVD7---/ - Switch input to input7</a></li>
<li><a href="/serial/IAVD8---/">/serial/IAVD8---/ - Switch input to input8</a></li>
<li><a href="/serial/IAVDQ---/">/serial/IAVDQ---/ - What's the current input?</a></li>
<li><a href="/serial/ITGD0---/">/serial/ITGD0---/ - Input toggle (moves to next input)</a></li>
<li><a href="/serial/DA2P0501/">/serial/DA2P0501/ - Set channel to Digital OTA 5.1</a></li>
<li><a href="/serial/DA2P1101/">/serial/DA2P1101/ - Set channel to Digital OTA 11.1</a></li>
<li><a href="/serial/DA2PQQQQ/">/serial/DA2PQQQQ/ - What's the current Digital OTA channel</a></li>
<li><a href="/serial/CHUP0---/">/serial/CHUP0---/ - Channel up</a></li>
<li><a href="/serial/CHDW0---/">/serial/CHDW0---/ - Channel down</a></li>
</ul><br>'''


@web_app.route("/serial/")
def serial(request: Request) -> Response:
    print(f"\n{request.method} {request.path}")
    response_html = html_doc("Serial interface", f"""{serial_commands()}
<a href="/" id="root">Back to root</a>""")
    print(response_html)
    return Response(request, body=response_html, content_type="text/html")


def serial_writer(code: str) -> Optional[str]:
    """Sends command to serial port and returns response"""
    print(f"Sending '{code}'")
    new_code = (code + '\r').encode('utf-8')
    r = uart.write(new_code)
    if r is not None:
        print(f"wrote {r} bytes")
    time.sleep(0.5)
    data = uart.read()
    result = None
    if data is not None:
        # the slice is trimming off the linefeed in the response
        result = ''.join([chr(b) for b in data[:-1]])
    return result


@web_app.route("/serial/<code>/")
def serial_write(request: Request, code: str) -> Response:
    print(f"\n{request.method} {request.path}")
    result = None
    unmunged = None
    if code is not None:
        unmunged = code.replace('-', ' ').replace('Q', '?')
        result = serial_writer(unmunged)
    response_html = html_doc("Serial interface", f"""Sent: {unmunged}<br><br>
Result: {result}<br><br>
{serial_commands()}
<a href="/" id="root">Back to root</a>""")
    print(response_html)
    return Response(request, body=response_html, content_type="text/html")


@web_app.route("/tv/")
def tv(request: Request) -> Response:
    print(f"\n{request.method} {request.path}")
    response_html = html_doc("tv interface", f"""Controls:<ul>
<li><a href="power/">power</a></li>
<li><a href="volume/">volume</a></li>
<li><a href="input/">input</a></li>
<li><a href="channel/">channel</a></li>
</ul><a href="/" id="root">Back to root</a>""")
    print(response_html)
    return Response(request, body=response_html, content_type="text/html")


@web_app.route("/tv/power/")
def tv_power(request: Request) -> Response:
    print(f"\n{request.method} {request.path}")
    result = None
    result_html = ""
    set_value = None
    status_value = None
    enable_value = None
    if request.method == "GET":
        set_value = request.query_params.get('set')
        status_value = request.query_params.get('status')
        enable_value = request.query_params.get('enable')
    if set_value is not None:
        if set_value in ('0', '1'):
            result = serial_writer(f"POWR{set_value}   ")
    elif status_value is not None:
        result = serial_writer("POWR?   ")
        if result == '0':
            result = 'Off'
        elif result == '1':
            result = 'On'
    elif enable_value is not None:
        if enable_value in ('0', '1'):
            result = serial_writer(f"RSPW{set_value}   ")
    if result is not None:
        result_html = f"Result: {result}<br>"
    response_html = html_doc(
        "tv power interface",
        f"""{result_html}Power: <a href="?set=1">On</a> <a href="?set=0">Off</a> <a href="?status=1">Status</a><br>
Power On command: <a href="?enable=1">Enable</a> <a href="?enable=0">Disable</a><br>
<a href="/tv/" id="tv">Back to tv</a>""")
    print(response_html)
    return Response(request, body=response_html, headers={'Access-Control-Allow-Origin': '*'}, content_type="text/html")


@web_app.route("/tv/volume/")
def tv_volume(request: Request) -> Response:
    print(f"\n{request.method} {request.path}")
    result = None
    result_html = ""
    v_value = None
    m_value = None
    if request.method == "GET":
        v_value = request.query_params.get('v')
        m_value = request.query_params.get('m')
    if v_value is not None:
        if v_value == 's':
            result = serial_writer("VOLM??  ")
        elif v_value.isdigit():
            v_int = int(v_value)
            if 0 <= v_int <= 60:
                result = serial_writer(f"VOLM{v_int:02d}  ")
    elif m_value is not None:
        if m_value == 's':
            result = serial_writer("MUTE?   ")
            if result == '2':
                result = 'Unmuted'
            elif result == '1':
                result = 'Muted'
        elif m_value in ('0', '1', '2'):
            result = serial_writer(f"MUTE{m_value}   ")
    if result is not None:
        result_html = f"Result: {result}<br>"
    response_html = html_doc(
        "tv volume interface",
        f"""{result_html}Volume: <a href="?v=4">4</a> <a href="?v=10">10</a> <a href="?v=15">15</a>
<a href="?v=s">Status</a><br>
Mute: <a href="?m=0">Toggle</a> <a href="?m=1">Mute</a> <a href="?m=2">Unmute</a> <a href="?m=s">Status</a><br>
<a href="/tv/" id="tv">Back to tv</a>""")
    print(response_html)
    return Response(request, body=response_html, headers={'Access-Control-Allow-Origin': '*'}, content_type="text/html")


@web_app.route("/tv/input/")
def tv_input(request: Request) -> Response:
    print(f"\n{request.method} {request.path}")
    result = None
    result_html = ""
    i_value = None
    if request.method == "GET":
        i_value = request.query_params.get('i')
    if i_value is not None:
        if i_value == 's':
            result = serial_writer("IAVD?   ")
        elif i_value == 't':
            result = serial_writer("ITVD0   ")
        elif i_value == 'x':
            result = serial_writer("ITGD0   ")
        elif i_value.isdigit():
            if 1 <= int(i_value) <= 8:
                result = serial_writer(f"IAVD{i_value}   ")
    if result is not None:
        result_html = f"Result: {result}<br>"
    response_html = html_doc(
        "tv input interface",
        f"""{result_html}Input: <a href="?i=t">Tuner</a>
<a href="?i=1">1</a> 
<a href="?i=2">2</a> 
<a href="?i=3">3</a> 
<a href="?i=4">4</a> 
<a href="?i=5">5</a> 
<a href="?i=6">6</a> 
<a href="?i=7">7</a> 
<a href="?i=8">8</a> 
<a href="?i=s">Status</a><br>
<a href="?i=x">Toggle</a><br>
<a href="/tv/" id="tv">Back to tv</a>""")
    print(response_html)
    return Response(request, body=response_html, headers={'Access-Control-Allow-Origin': '*'}, content_type="text/html")


@web_app.route("/tv/channel/")
def tv_channel(request: Request) -> Response:
    print(f"\n{request.method} {request.path}")
    result = None
    result_html = ""
    c_value = None
    if request.method == "GET":
        c_value = request.query_params.get('c')
    if c_value is not None:
        if c_value == 's':
            result = serial_writer("DA2P????")
        elif c_value == 'u':
            result = serial_writer("CHUP0   ")
        elif c_value == 'd':
            result = serial_writer("CHDW0   ")
        elif c_value.isdigit():
            result = serial_writer(f"DA2P{c_value}")
    if result is not None:
        result_html = f"Result: {result}<br>"
    response_html = html_doc(
        "tv channel interface",
        f"""{result_html}Channel: <a href="?c=s">Status</a>
<a href="?c=0501">5.1</a> 
<a href="?c=1101">11.1</a><br>
<a href="?c=u">Up</a> <a href="?c=d">Down</a><br>
<a href="/tv/" id="tv">Back to tv</a>""")
    print(response_html)
    return Response(request, body=response_html, headers={'Access-Control-Allow-Origin': '*'}, content_type="text/html")


def html_doc(title: str, body: str) -> str:
    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" href="data:,">
<title>{title}</title>
<style>body{{background-color:#0d1117;color:#ffffff;}}a{{color:#5b9ce6;}}</style></head>
<body>
{body}
</body></html>'''


@web_app.route("/")
def root(request: Request) -> Response:
    print(f"\n{request.method} {request.path}")
    mac = ":".join("%02X" % _ for _ in eth.mac_address)
    ip = eth.pretty_ip(eth.ip_address)
    temp = microcontroller.cpu.temperature * (9 / 5) + 32
    response_html = html_doc("WIZnet W5100S-EVB-Pico web UI", f'''<div>
<h1>WIZnet W5100S-EVB-Pico web server</h1>
<h2>Hardware Information</h2>
<p>Chip Version: {eth.chip}<br>MAC Address: {mac}<br>
IP Address: {ip}<br>CPU Temperature: {temp} F<br></p>
<h2>Services</h2>
<p><a href="/led/" id="led">/led/ - Control the green user LED</a><br></p>
<p><a href="/serial/" id="w_uart">/serial/ - write to serial</a><br></p>
<p><a href="/tv/" id="tv">/tv/ - control the tv</a><br></p>
</div>''')
    print(response_html)
    return Response(request, body=response_html, content_type="text/html")


@web_app.route("/bootloader/")
def bootloader(request):  # pylint: disable=unused-argument
    """Reboot into bootloader via web request, e.g. to upgrade CircuitPython"""
    print("\nreboot into bootloader")
    microcontroller.on_next_reset(microcontroller.RunMode.BOOTLOADER)
    microcontroller.reset()


@web_app.route("/reboot/")
def reboot(request):  # pylint: disable=unused-argument
    """Reboot via web request"""
    print("\nreboot request received")
    microcontroller.reset()


# Here we set up our server, passing in our web_app as the application
print("Starting WSGI server")
web_app.start(host=str(eth.pretty_ip(eth.ip_address)), port=80)

print("Open this IP in your browser: ", eth.pretty_ip(eth.ip_address))

while True:
    # Our main loop where we have the server poll for incoming requests
    web_app.poll()
    # Maintain DHCP lease
    eth.maintain_dhcp_lease()
    gc.collect()
