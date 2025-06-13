from .dev import DevConfig
from .prod import ProdConfig

config_by_name = dict(
    dev=DevConfig,
    prod=ProdConfig
)
