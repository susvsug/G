const { REST, Routes } = require("discord.js");
const fs = require("fs");
const path = require("path");
const config = require("./config");

const commands = [];

const commandsPath = path.join(__dirname, "commands");

const commandFiles = fs
    .readdirSync(commandsPath)
    .filter(file => file.endsWith(".js"));

for (const file of commandFiles) {

    const command = require(path.join(commandsPath, file));

    commands.push(command.data.toJSON());

}

const rest = new REST({ version: "10" }).setToken(config.token);

(async () => {

    try {

        console.log("Registering Slash Commands...");

        await rest.put(
            Routes.applicationGuildCommands(
                config.clientId,
                config.guildId
            ),
            {
                body: commands
            }
        );

        console.log("Slash Commands Registered!");

    } catch (err) {

        console.error(err);

    }

})();
