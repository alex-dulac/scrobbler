class MacOSSystemInfo:
    def __init__(self,
                 user_name: str | None = None,
                 long_user_name: str | None = None,
                 user_id: int | None = None,
                 home_dir: str | None = None,
                 boot_volume: str | None = None,
                 system_version: str | None = None,
                 cpu_type: str | None = None,
                 physical_memory: int | None = None,
                 user_locale: str | None = None
                 ):
        self.user_name = user_name
        self.long_user_name = long_user_name
        self.user_id = user_id
        self.home_dir = home_dir
        self.boot_volume = boot_volume
        self.system_version = system_version
        self.cpu_type = cpu_type
        self.physical_memory = physical_memory
        self.user_locale = user_locale
