import requests
from valor import Valor
from sql import ValorSQL
from util import ErrorEmbed, HelpEmbed, LongFieldEmbed, LongTextEmbed, sinusoid_regress
from discord.ext.commands import Context
from datetime import datetime
from discord import File
from collections import defaultdict
import logging
from dotenv import load_dotenv
import argparse
from PIL import Image, ImageDraw, ImageFont
import zlib
from .common import guild_name_from_tag, guild_tag_from_name
import json

load_dotenv()
with open("assets/map_regions.json") as f:
    map_regions = json.load(f)

async def _register_map(valor: Valor):
    desc = "100 percent an Athena knockoff"
    parser = argparse.ArgumentParser(description='Map command')
    parser.add_argument('-g', '--guild', nargs='+')
    parser.add_argument('-z', '--zones', nargs='+')
    parser.add_argument('-r', '--routes', action='store_true')
    main_map = Image.open("assets/main-map.png") # like 10MB ish
    font = ImageFont.load_default()
    map_width, map_height = main_map.size

    terr_conn_lookup = None

    def to_full_map_coord(x_ingame, y_ingame):
        # (-1614 -2923) (x,y) center of corkus -> (192 913) (x, canvas y)
        # (-1609 -2943) (x,y) center of corkus balloon -> (193 908) (x, canvas y)
        x_canvas = (x_ingame+2382)*map_width/4034 # do linalg.solve to compute the weights
        y_canvas = (y_ingame+6572)*map_height/6414

        return x_canvas, y_canvas
    
    def get_col_tuple(x, alpha):
        return ((x >> 16) & 0xFF, (x >> 8) & 0xFF, x & 0xFF, alpha)
    
    @valor.command()
    async def map(ctx: Context, *options):
        # closure capture reference
        nonlocal terr_conn_lookup # I really didn't know about this feature. Better than static class var
        if not terr_conn_lookup:
            with open("assets/terr_conns.json", 'r') as f:
                terr_data = json.load(f)
            terr_conn_lookup = defaultdict(list)
            for k in terr_data:
                terr_conn_lookup[k] = terr_data[k]["Trading Routes"]
        
        try:
            opt = parser.parse_args(options)
        except:
            return await LongTextEmbed.send_message(valor, ctx, "Map", parser.format_help().replace("main.py", "-map"), color=0xFF00)
        
        try:
            athena_terr_res = requests.get("https://athena.wynntils.com/cache/get/territoryList").json()
        except:
            athena_terr_res = None
            logging.error("Athena is down")

        # use avomap colors for now
        # athena_colors = requests.get("https://athena.wynntils.com/cache/get/guildListWithColors").json()
        # guild_to_color = {athena_colors[k]["_id"]: athena_colors[k]["color"] for k in athena_colors}

        guild_to_color = requests.get("https://www.avicia.info/api/guildcolors").json()

        Y_or_Z = "Z"     
        if not athena_terr_res or not "territories" in athena_terr_res or len(athena_terr_res["territories"]) == 0:
            # Temporary solution until perhaps athena adapts the format.
            wynn_terr_res = requests.get("https://api.wynncraft.com/v3/guild/list/territory").json()
            for territory, data in wynn_terr_res.items():
                wynn_terr_res[territory] = {
                    "territory": territory,
                    "guild": data["guild"]["name"],
                    "guildPrefix": data["guild"]["prefix"],
                    "location": {
                        "startX": data["location"]["start"][0],
                        "startY": data["location"]["start"][1],
                        "endX": data["location"]["end"][0],
                        "endY": data["location"]["end"][1],
                    }
                }
            athena_terr_res["territories"] = wynn_terr_res.copy()
            del wynn_terr_res
                
            Y_or_Z = "Y"
        interested_guild_tags = set(opt.guild) if opt.guild else set()
        
        interest_guild_names = set([await guild_name_from_tag(x) for x in interested_guild_tags])

        # no more alliance. just mark every territory as our guild claim.
        # res = await ValorSQL._execute("SELECT * FROM ally_claims")
        claim_owner = {}
        for terr in athena_terr_res["territories"].keys():
            claim_owner[terr] = "Titans Valor"

        terr_details = {}
        x_lo = y_lo = float("inf")
        x_hi = y_hi = float("-inf")

        edge_list = []
        edge_list_done = set()
        terr_count = {}

        for terr in athena_terr_res["territories"]:
            x0 = athena_terr_res["territories"][terr]["location"]["startX"]
            y0 = athena_terr_res["territories"][terr]["location"]["start"+Y_or_Z]
            x1 = athena_terr_res["territories"][terr]["location"]["endX"]
            y1 = athena_terr_res["territories"][terr]["location"]["end"+Y_or_Z]
            holder = athena_terr_res["territories"][terr]["guild"]
            terr_details[terr] = {
                "holder": holder,
                # "holder_color": athena_terr_res["territories"][terr].get("guildColor", ''), old way
                "holder_color": guild_to_color.get(holder, ''),
                "holder_prefix": athena_terr_res["territories"][terr].get("guildPrefix"),
                "adj": terr_conn_lookup[terr],
                "x0": x0,
                "y0": y0,
                "x1": x1,
                "y1": y1
            }

            if opt.routes:
                neighbors = terr_conn_lookup[terr]
                for n in neighbors:
                    if (terr, n) in edge_list_done or (n, terr) in edge_list_done: continue
                    edge_list_done.add((n, terr))
                    n_x0 = athena_terr_res["territories"][n]["location"]["startX"]
                    n_y0 = athena_terr_res["territories"][n]["location"]["start"+Y_or_Z]
                    n_x1 = athena_terr_res["territories"][n]["location"]["endX"]
                    n_y1 = athena_terr_res["territories"][n]["location"]["end"+Y_or_Z]
                    edge_list.append(((x0+x1)/2, (y0+y1)/2, (n_x0+n_x1)/2, (n_y0+n_y1)/2))

            if not terr_details[terr]["holder"] in interest_guild_names and opt.guild: continue
            
            terr_count[terr_details[terr]["holder"]] = terr_count.get(terr_details[terr]["holder"], 0)+1
            if opt.zones:
                outside_zone = 0
                for z in opt.zones:
                    zx1, zy1, zx2, zy2 = map_regions[z.lower()]
                    zx1, zy1, zx2, zy2 = min(zx1, zx2), min(zy1, zy2), max(zx1, zx2), max(zy1, zy2) # just to make sure bot left to top right order
                    if not ((x0+x1)/2 >= zx1 and (x0+x1)/2 <= zx2 and (y0+y1)/2 >= zy1 and (y0+y1)/2 <= zy2):
                        outside_zone += 1
                if outside_zone == len(opt.zones):
                    continue
            x_lo = min(x_lo, min(x0, x1))
            x_hi = max(x_hi, max(x0, x1))
            y_lo = min(y_lo, min(y0, y1))
            y_hi = max(y_hi, max(y0, y1))
  
        # map goes from left upper to right lower world coordinates
        # following vars are 
        x_lo_full, y_lo_full = to_full_map_coord(x_lo, y_lo)
        x_hi_full, y_hi_full = to_full_map_coord(x_hi, y_hi)

        x_lo_full = max(0, x_lo_full-50) # extend the boundaries
        y_lo_full = max(0, y_lo_full-50) # extend the boundaries
        x_hi_full = min(map_width, x_hi_full+50) # extend the boundaries
        y_hi_full = min(map_height, y_hi_full+50) # extend the boundaries
    
        if not sum(terr_count.values()):
            return await LongTextEmbed.send_message(valor, ctx, f"Map", 
                "None of the requested guilds control any territories.", color=0xFF0000)
        
        no_territories = [k for k in terr_count.keys() | interest_guild_names if not k in terr_count or terr_count[k] == 0]
        no_territories_msg = f"The following control 0 territories: {no_territories}\n\n" if no_territories else ""

        section = main_map.crop((x_lo_full, y_lo_full, x_hi_full, y_hi_full))
        section_layer = Image.new("RGBA", section.size, (255, 255, 255, 0))
        section_draw = ImageDraw.Draw(section_layer, "RGBA")
        # draw route lines
        for edge in edge_list:
            x0, y0 = to_full_map_coord(*edge[:2])
            x1, y1 = to_full_map_coord(*edge[2:])
            x0 -= x_lo_full
            y0 -= y_lo_full
            x1 -= x_lo_full
            y1 -= y_lo_full
            section_draw.line((x0, y0, x1, y1), width=3, fill=get_col_tuple(0xFFFFFF, 255))
        section = Image.alpha_composite(section, section_layer)

        tag_to_guild = {}

        # draw boxes around terrs and stuff
        for claim, guild in claim_owner.items():
            x0, y0 = to_full_map_coord(terr_details[claim]["x0"], terr_details[claim]["y0"])
            x1, y1 = to_full_map_coord(terr_details[claim]["x1"], terr_details[claim]["y1"])
            x0 -= x_lo_full
            y0 -= y_lo_full
            x1 -= x_lo_full
            y1 -= y_lo_full
            col_str = terr_details[claim]["holder_color"][1:]
            holder_guild = terr_details[claim]["holder"]

            if not col_str:
                gu_color = zlib.crc32(holder_guild.encode("utf8")) & 0xFFFFFF
            else:
                gu_color = int(col_str if col_str else "0", 16)

            holder_pfx = terr_details[claim]["holder_prefix"]
            if not holder_pfx:
                if not holder_guild in tag_to_guild:
                    tag_to_guild[holder_guild] = await guild_tag_from_name(holder_guild)
                holder_pfx = tag_to_guild[holder_guild]

            x0, x1 = min(x0, x1), max(x0, x1)
            y0, y1 = min(y0, y1), max(y0, y1)
            section_draw.rectangle((x0, y0, x1, y1), fill=get_col_tuple(gu_color, 64), outline=get_col_tuple(gu_color, 200), width=2)
            if terr_details[claim]["holder"] != claim_owner[claim]: # disputed terr
                y_i = min(y0, y1)
                i = 0
                while y_i < max(y0, y1):
                    if i % 2 == 0:
                        section_draw.rectangle((x0, y_i, x1, min(max(y0, y1), y_i+5)), fill=get_col_tuple(0xFFFFFF, 64), outline=get_col_tuple(gu_color, 200), width=1)
                    i += 1
                    y_i += 5
                
            section_draw.text(((x0+x1-16*len(holder_pfx)/2)/2-1, (y0+y1-18)/2-1), holder_pfx, fill=get_col_tuple(0x00, 255), font=font)
            section_draw.text(((x0+x1-16*len(holder_pfx)/2)/2+1, (y0+y1-18)/2+1), holder_pfx, fill=get_col_tuple(0x00, 255), font=font)
            section_draw.text(((x0+x1-16*len(holder_pfx)/2)/2, (y0+y1-18)/2), holder_pfx, fill=get_col_tuple(0xFFFFFF, 255), font=font)

        section = Image.alpha_composite(section, section_layer)
        section.convert("RGB").save("/tmp/map_output.png")
        file = File("/tmp/map_output.png", filename="map.png")

        warn_athena_down = "Athena API is down (WynnAPI as fallback) Colors may be wrong.!!!\n\n" if Y_or_Z == "Y" else ""

        await ctx.send(file=file)

        if warn_athena_down:
            await LongTextEmbed.send_message(valor, ctx, f"Map", no_territories_msg+warn_athena_down, color=0xFF0000, 
                # url="attachment://map.jpg",
            )

        # main_map.close() don't actually close it

    @valor.help_override.command()
    async def map(ctx: Context):
        await LongTextEmbed.send_message(valor, ctx, "Map", desc, color=0xFF00)
