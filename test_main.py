import unittest
from unittest.mock import patch, AsyncMock, MagicMock
import asyncio
import discord
import valor
import commands
import listeners
import ws
import cron
from sql import ValorSQL

class TestMain(unittest.TestCase):

    @patch('valor.Valor')
    @patch('discord.Intents.all', return_value=MagicMock())
    @patch('aiomysql.create_pool', new_callable=AsyncMock)
    @patch('commands.register_all', new_callable=AsyncMock)
    @patch('listeners.register_all', new_callable=AsyncMock)
    @patch('ws.register_all', new_callable=AsyncMock)
    @patch('cron.gxp_roles', new_callable=AsyncMock)
    @patch('cron.warcount_roles', new_callable=AsyncMock)
    @patch('cron.ticket_cron.start', new_callable=AsyncMock)
    def test_main(self, mock_ticket_cron_start, mock_gxp_roles, mock_warcount_roles, mock_ws_register_all, mock_listeners_register_all, mock_commands_register_all, mock_create_pool, mock_intents_all, mock_valor):
        # Mock the valor instance
        mock_valor_instance = mock_valor.return_value
        mock_valor_instance.loop = asyncio.get_event_loop()

        async def mock_main():
            @mock_valor_instance.event
            async def on_ready():
                await mock_valor_instance.tree.sync()
                await mock_ticket_cron_start(mock_valor_instance)

            async with mock_valor_instance:
                ValorSQL.pool = await mock_create_pool(**ValorSQL._info, loop=mock_valor_instance.loop)
                
                await mock_commands_register_all(mock_valor_instance)
                await mock_listeners_register_all(mock_valor_instance)
                await mock_ws_register_all(mock_valor_instance)
                
                await asyncio.gather(
                    mock_valor_instance.start('-'),
                    mock_gxp_roles(mock_valor_instance),
                    mock_warcount_roles(mock_valor_instance)      
                )

        asyncio.run(mock_main())

        # Assertions to ensure all mocks were called
        mock_valor.assert_called_once_with('-', intents=mock_intents_all)
        mock_create_pool.assert_called_once_with(**ValorSQL._info, loop=mock_valor_instance.loop)
        mock_commands_register_all.assert_called_once_with(mock_valor_instance)
        mock_listeners_register_all.assert_called_once_with(mock_valor_instance)
        mock_ws_register_all.assert_called_once_with(mock_valor_instance)
        mock_gxp_roles.assert_called_once_with(mock_valor_instance)
        mock_warcount_roles.assert_called_once_with(mock_valor_instance)
        mock_ticket_cron_start.assert_called_once_with(mock_valor_instance)

if __name__ == '__main__':
    unittest.main()
