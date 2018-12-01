# Lines that are empty or start with # will be ignored.
# Values within "" will be treated as strings, while
# others will be treated as integers or floats.
# Call on main file as SETTINGS.name

class SETTINGS:
    ########################################################
    #   BOT SETTINGS                                       #
    ########################################################
    # Max results shown per Google search.
    # Note that it only looks at the first page, so values
    # over 10 will be pointless.
    MAX_GOOGLE_RESULTS = 3
    
    # ID of the server. Shouldn't ever change but just in
    # case.
    SERVER_ID = "237325019770912769"
    
    # ID of the bot. Shouldn't ever change but just in
    # case.
    BOT_ID = "389619827905527819"
    
    # List of users that qualift as devs. For future use.
    DEV_ID = [
                "108402088215597056",  # Gai
                "110913872273117184",  # Zy
             ]
    
    # IDs of channels.
    CHANNEL_ID = [
                    "237325019770912769",  # general
                    "237328152240586753"   # images
                 ]
    
    # Max amount of messages search for batch deletion.
    MAX_DELETE_SEARCH = 50

    # Debug mode: Prints information about command functions
    # 0 -> Print nothing
    # 1 -> Print basic things (Command read, results)
    # 2 -> Print more advanced stuff (HTML, timer progress)
    DEBUG_MODE = 1

    # Maintenance/test mode. Only allow commands if sent by DEV_ID
    MAINTENANCE_MODE = False

    # Timer decrease interval and wait amount (Update every X seconds)
    TIMER_WAIT = 7
    
    ########################################################
    #   OTHER SETTINGS                                     #
    ########################################################
    # MAL search API requires an auth. Change if you want
    # to use the shitty API instead of HTML scrapping.
    MAL_USER = ""
    MAL_PASS = ""

    # Which elements of MAL "Information" are to be shown.
    MAL_INFO = [
                    "Type",
                    "Episodes",
                    "Aired",
                    "Studios",
                    "Genres",
                    "Duration",
                    "Volumes",
                    "Chapters",
                    "Status",
                    "Authors"
               ]
    
    # ID used for imgur upload.
    IMGUR_ID = "a11d867ed31f8fd"

    COMMAND_LIST = [
                        "gelbooru",
                        "reminder"
                   ]