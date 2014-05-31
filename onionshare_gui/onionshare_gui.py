#!/usr/bin/env python

import onionshare, webgui
import os, sys, time, json, gtk, thread

class Global(object):
    quit = False
    @classmethod
    def set_quit(cls, *args, **kwargs):
        cls.quit = True

def alert(msg, type=gtk.MESSAGE_INFO):
    dialog = gtk.MessageDialog(
        parent=None,
        flags=gtk.DIALOG_MODAL,
        type=type,
        buttons=gtk.BUTTONS_OK,
        message_format=msg)
    response = dialog.run()
    dialog.destroy()

def select_file(strings):
    # get filename, either from argument or file chooser dialog
    if len(sys.argv) == 2:
        filename = sys.argv[1]
    else:
        canceled = False
        chooser = gtk.FileChooserDialog(
            title="Choose a file to share",
            action=gtk.FILE_CHOOSER_ACTION_OPEN,
            buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        response = chooser.run()
        if response == gtk.RESPONSE_OK:
            filename = chooser.get_filename()
        elif response == gtk.RESPONSE_CANCEL:
            canceled = True
        chooser.destroy()

        if canceled:
            return False, False

    # validate filename
    if not os.path.isfile(filename):
        alert(strings["not_a_file"].format(filename), gtk.MESSAGE_ERROR)
        return False, False

    filename = os.path.abspath(filename)
    basename = os.path.basename(filename)
    return filename, basename

def main():
    strings = onionshare.load_strings()

    # try starting hidden service
    port = onionshare.choose_port()
    try:
        onion_host = onionshare.start_hidden_service(port)
    except onionshare.NoTor as e:
        alert(e.args[0], gtk.MESSAGE_ERROR)
        return

    # select file to share
    filename, basename = select_file(strings)
    if not filename:
        return

    # open the window, launching webkit browser
    webgui.start_gtk_thread()
    browser, web_recv, web_send = webgui.sync_gtk_msg(webgui.launch_window)(
        title="OnionShare | {0}".format(basename),
        quit_function=Global.set_quit)
    time.sleep(0.1)

    # startup
    web_send("init('{0}', {1});".format(basename, json.dumps(strings)))
    web_send("update('{0}')".format(strings['calculating_sha1']))
    filehash, filesize = onionshare.file_crunching(filename)
    onionshare.set_file_info(filename, filehash, filesize)
    onionshare.tails_open_port(port)
    url = 'http://{0}/{1}'.format(onion_host, onionshare.slug)
    web_send("update('{0}')".format('Secret URL is {0}'.format(url)))
    web_send("set_url('{0}')".format(url));

    # start the web server
    web_thread = thread.start_new_thread(onionshare.app.run, (), {"port": port})

    # main loop
    last_second = time.time()
    uptime_seconds = 1
    clicks = 0
    while not Global.quit:

        current_time = time.time()
        again = False
        msg = web_recv()
        if msg:
            msg = json.loads(msg)
            again = True

        # check msg for messages from the browser
        # use web_send() to send javascript to the browser

        if not again:
            time.sleep(0.1)

    # shutdown
    onionshare.tails_close_port(port)

if __name__ == '__main__':
    main()
