#!/Users/erik/projects/check-proxies/.venv/bin/python

'''
    This program is designed to check your proxy list and output results.
    The working results will be saved to 'valid-proxies.txt' and to stdout.

    You can change a number of options:
        Number of threads to use can be changed from THREAD_COUNT
        Output file can be changed using OUTFILE
        Log level can be changed to output more info using LOG_LEVEL
        You can change to site to check against using SITE variable. It can be anything (google, ip-api.com, ...)
'''

import threading
import queue
import requests
import logging
import sys


#==============Options=============#
OUTFILE = "valid-proxies.txt"
SITE :str = "https://check-host.net/"
FILENAME :str = ""
THREAD_COUNT = 8 # number of threads to use
LOG_LEVEL = logging.ERROR
#===================================


HELP :str = '''Usage: cproxy.py <proxy_list>    Filter proxies that actually work
<proxy_list> -   Path to the file containing proxies

NOTE: The proxy file should contain a proxy perline in the form:
    scheme://ip:port. scheme can be anything e.g. (socks5, http, https
'''

VALID_PROXIES :set = set()
LOCK = threading.Lock()
PROXY_QUEUE = queue.Queue()
STOPEVENT = threading.Event()


logging.basicConfig(
    level=LOG_LEVEL,
    format='%(lineno)s %(levelname)s - %(message)s',
    filename='log',
    filemode='w'
)



def read_proxies() -> None:
    try:
        with open(FILENAME, 'r') as file_stream:
            for line in file_stream:
                current_proxy = line.strip()
                if not current_proxy.startswith(("socks", "http")):
                    raise Exception("scheme not recognized!")

                if current_proxy: # ignore empty lines
                    logging.debug(f"Adding proxy to the queue: {current_proxy}")
                    PROXY_QUEUE.put(current_proxy)
    except FileNotFoundError:
        print("File doesn't exist!")
        exit(1)
    except Exception as ex:
        print(ex)
        exit(1)

def check_proxy() -> None:
    global PROXY_QUEUE
    while not (PROXY_QUEUE.empty() or STOPEVENT.is_set()):
        logging.debug("Reading proxy from queue")
        proxy = PROXY_QUEUE.get()

        try:
            logging.debug("Checking proxy connection...")
            res = requests.get(
                SITE,
                proxies={'http': proxy, 'https': proxy},
                timeout=2
            )
        except:
            logging.debug("Proxy didn't work! Moving on...")
            continue

        if res.status_code == 200:
            logging.info("Proxy worked. Adding to valid proxies...")
            print(proxy)
            with LOCK:
                VALID_PROXIES.add(proxy)

def onquit() -> None:
    # it overrides any existing file
    with open(OUTFILE, 'w') as filestream:
        filestream.write('\n'.join(VALID_PROXIES))
        filestream.write('\n')


def main() -> None:
    global FILENAME
    try:
        logging.debug("Getting file name in argv")
        FILENAME = sys.argv[1]
    except Exception as e:
        print(e)
        print(HELP)
        exit(1)

    logging.info("Reading proxies from list...")
    read_proxies()

    if PROXY_QUEUE.qsize == 0:
        print("No proxies found. Quiting...")
        exit(1)

    threads = []
    logging.info(f"Starting {THREAD_COUNT} threads for testing")
    for _ in range(THREAD_COUNT):
        t = threading.Thread(target=check_proxy)
        t.start()
        threads.append(t)

    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print("=====program interrupted. writing the results...======")
        STOPEVENT.set()
        for t in threads:
            t.join()
        onquit()
        exit()
    
    # write results and quit
    onquit()

if __name__ == '__main__':
    main()

