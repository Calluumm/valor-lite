from .online import _register_online
from .help import _register_help
from .preferences import _register_preferences
from .gxp import _register_gxp
from .guild import _register_guild
from .plot import _register_plot
from .activity import _register_activity
from .profile import _register_profile
from .join import _register_join
from .plot2 import _register_plot2
from .avg import _register_avg
from .leaderboard import _register_leaderboard
from .leaderboard_old import _register_leaderboard_old
from .map import _register_map
from .coolness import _register_coolness
from .up import _register_up
from .alliance import _register_alliance
from .history import _register_history
from .warcount_old import _register_warcount_old
from .sus import _register_sus
from .blacklist import _register_blacklist
from .warcount import _register_warcount
from .inspire import _register_inspire
from .update_stats import _register_update_stats 
from .inactivity import _register_inactivity
from .raids import _register_raids
from .completion import _register_completion
from .HQ import _register_HQ
from .graids import _register_graids
from valor import Valor
from discord.ext.commands.hybrid import HybridCommand

async def register_all(valor: Valor):
    """
    Registers all the commands"
    """
    await _register_help(valor)
    await _register_online(valor)
    await _register_preferences(valor)
    await _register_gxp(valor)
    await _register_guild(valor)
    await _register_plot(valor)
    await _register_activity(valor)
    await _register_profile(valor)
    await _register_pm(valor)
    await _register_join(valor)
    await _register_plot2(valor)
    await _register_avg(valor)
    await _register_leaderboard(valor)
    await _register_leaderboard_old(valor)
    await _register_coolness(valor)
    await _register_up(valor)
    await _register_alliance(valor)
    await _register_history(valor)
    await _register_warcount_old(valor)
    await _register_map(valor)
    await _register_sus(valor)
    await _register_blacklist(valor)
    await _register_warcount(valor)
    await _register_inspire(valor)
    await _register_update_stats(valor)
    await _register_inactivity(valor)
    await _register_raids(valor)
    await _register_completion(valor)
    await _register_HQ(valor)
    await _register_graids(valor)
    
