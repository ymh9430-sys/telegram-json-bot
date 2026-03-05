const axios = require("axios");

async function getToken() {

    const res = await axios.get("https://music.apple.com");

    const match = res.data.match(/"developerToken":"(.*?)"/);

    if (!match) {
        throw new Error("Token not found");
    }

    return match[1];
}

module.exports = getToken;
