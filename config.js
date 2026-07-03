require("dotenv").config();

module.exports = {
    token: process.env.TOKEN,
    clientId: process.env.CLIENT_ID,
    guildId: process.env.GUILD_ID,

    boosterRoleId: process.env.BOOSTER_ROLE_ID,
    logChannelId: process.env.LOG_CHANNEL_ID,

    maxSharedMembers: 3,

    embed: {
        color: 0x5865F2
    }
};
