/**
 * Project Blackout PVP – website configuration
 *
 * Enter your server details here. Every page picks the values up
 * automatically wherever they are shown (status bar, join guide,
 * server info, footer …).
 */
window.BLACKOUT_CONFIG = {
  // Server IP and game port (displayed and copied on click)
  ip: '203.0.113.10',
  port: '2302',

  // Map running on the server (e.g. Chernarus, Livonia, Deer Isle …)
  map: 'Chernarus',

  // Maximum number of players
  maxPlayers: 60,

  // Invite link to your Discord
  discord: 'https://discord.gg/YOUR-INVITE',

  // Restart schedule in server time (24h format) and the server's time zone.
  // Powers the "Next restart" countdown. Leave the list empty to hide it.
  restartTimes: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00'],
  timezone: 'Europe/Berlin',

  // Required mods – listed on the Join and Server pages.
  // Leave the list empty to hide the mod list.
  // Example: { name: 'Community Framework', url: 'https://steamcommunity.com/sharedfiles/filedetails/?id=…' },
  mods: [],

  // Optional: BattleMetrics server ID for live status and player count.
  // It's the number at the end of the URL, e.g. battlemetrics.com/servers/dayz/1234567 → '1234567'.
  // Leave empty to hide the live status.
  battlemetricsId: '',
};
