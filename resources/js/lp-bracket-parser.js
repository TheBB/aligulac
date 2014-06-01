lp_pattern = /\s*{{(\d+)SEBracket([\s\S]*)}}\s*/im;
lp_prop_pattern = /\s*R(\d+)(W|D)(\d+)(.*?)=(.*?)\s*$/i;

log2 = {
    2 : 1,
    4 : 2,
    8 : 3,
    16 : 4,
    32 : 5,
    64 : 6,
    128 : 7
};
pow2 = [1, 2, 4, 8, 16, 32, 64, 128];

function showLPButton() {
    document.getElementById("lp_button").style.display = "";
}

function hideLPButton() {
    document.getElementById("lp_button").style.display = "none";
}

function format_change(el) {
    if (el.selectedIndex == 2)
        showLPButton();
    else
        hideLPButton();
}

function parseLP() {
    var text = document.getElementById("players").value;
    var result = parseBracket(text);
    document.getElementById("players").value = result;
}

function parseBracket(text) {
    
    var match = text.match(lp_pattern);
    
    var numPlayers = +match[1];
    var numRounds = log2[numPlayers];

    /* Remove HTML comments. */
    var propText = match[2].replace(/(<!--.*?-->)/gim, "");
    

    /* A list of matches for each round. */
    var properties = {};
    for (var i = 0; i < numRounds; i++) {
        properties[i] = {};
        var players = pow2[numRounds-i];
    
        for (var j = 0; j < players / 2; j++) {
            /* Each match contains two players. */
            properties[i][j] = [{}, {}];
            properties[i][j][0].opponent = properties[i][j][1];
            properties[i][j][1].opponent = properties[i][j][0];
        }
    }
    
    var propList = propText.split("|");

    /* Read through all properties */
    for (var i in propList) {

        var prop = propList[i];
        match = prop.match(lp_prop_pattern);
    
        /* 
           This gives a list as follows:
           [ _, round, W|D, player, propName, propValue ] 
           e.g
           [ _, 1, "D", 1, "", "TargA"]
           [ _, 1, "D", 1, "race", "z"]
        */
        if (match != undefined) {
            var round = +match[1];
            var player = +match[3];
            var propName = match[4];
            var propValue = match[5];

            player = player - 1;
            match = Math.floor(player / 2) ;
            player = player % 2;
            round = round - 1;

            /* Put it where it belongs! */
            properties[round][match][player][propName] = propValue;
        }
    } 

    /* Iterate through players to determine byes */
    var result = [];

    for (var i = 0; i < numPlayers; i++ ) {
        if (isOut(properties, 0, i))
            result.push("-");
        else {
            var player = properties[0][Math.floor(i / 2)][i % 2]
            var p = player[""];
            if (player["flag"] != undefined)
                p += " " + player["flag"];
            if (player["race"] != undefined)
                p += " " + player["race"];
            result.push(p);
        }
    }

    return result.join("\n");
}

function isOut(properties, round, pid)
{
    var match = Math.floor(pid / 2)
    var player = properties[round][match][pid % 2];
    /* 
       If the opponent has won it means that player is out.
       If the player won we have to look at the next match.
       If no-one has won yet it means that the player is still in
          the bracket and is not out.
    */
    if (player.opponent["win"] == 1)
        return true;
    if (player["win"] == 1)
        return isOut(properties, round + 1, match);
    
    return false;
}
