const axios = require("axios");
const xml2js = require("xml2js");
const getToken = require("./token");

async function getLyrics(songId){

    const token = await getToken();

    const url = `https://amp-api.music.apple.com/v1/catalog/us/songs/${songId}/lyrics`;

    const res = await axios.get(url,{
        headers:{
            Authorization:`Bearer ${token}`,
            Origin:"https://music.apple.com",
            Referer:"https://music.apple.com/"
        }
    });

    const ttml = res.data.data[0].attributes.ttml;

    const parser = new xml2js.Parser();
    const parsed = await parser.parseStringPromise(ttml);

    const lines = parsed.tt.body[0].div[0].p;

    let lrc = "";

    lines.forEach(line => {

        const time = line.$.begin;
        const text = line._ || "";

        lrc += `[${time}] ${text}\n`;
    });

    return lrc;
}

module.exports = getLyrics;
