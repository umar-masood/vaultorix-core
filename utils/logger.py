import logging

# Logger
log = logging.Logger("Vaultorix", level = logging.DEBUG)

# Formatter
formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(filename)s:%(lineno)d | %(message)s")

# File Handler
file_handler = logging.FileHandler(filename = "vaultorix.log", mode = 'a')
file_handler.setFormatter(formatter)

# Console Hanlder
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# Adding handlers to logging
log.addHandler(file_handler)
