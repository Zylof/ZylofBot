# Lines that are empty or start with # will be ignored.
# Values within "" will be treated as strings, while
# others will be treated as integers or floats.
# Call on main file as SETTINGS.name

class FOLDERS:
    ########################################################
    #   FOLDERS                                            #
    ########################################################
    # All folders are to be relative to the main bot source
    # Use dict table for multiple os -> Refer to os.name
    # For ease, always end with "\" or "/" or equivalent

    ANIME_PICS = {
                    "nt" : "\\Files\\animu\\",
                    "posix" : "/Files/animu/"
    }

    RIKA_PICS = {
                    "nt" : "\\Files\\animu\\higu\\",
                    "posix" : "/Files/animu/higu/"
    }

    TAIGA_PICS = {
                    "nt" : "\\Files\\Taiga\\",
                    "posix" : "/Files/Taiga/"
    }

    EMOJI_DOWNLOAD = {
                    "nt" : "\\Files\\EmojiDownload\\",
                    "posix" : "/Files/EmojiDownload/"
    }

    THUMBNAIL_DOWNLOAD = {
                    "nt" : "\\Files\\Thumbnails\\",
                    "posix" : "/Files/Thumbnails/"
    }