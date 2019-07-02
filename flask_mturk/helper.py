

# Helper function to convert timeunit to int #
def seconds_from_string(string):
    if string == 'minutes':
        return 60
    if string == 'hours':
        return 60 * 60
    if string == 'days':
        return 24 * 60 * 60
    return -1


# Helper function to check if string is integer #
def is_number(string):
    try:
        int(string)
        return True
    except ValueError:
        return False
