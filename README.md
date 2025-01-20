<div align="center">
  <a href="https://mapink.sarim.uk">
    <img src="https://i.imgur.com/LUTaSX2.png" alt="CS2Stats" />
  </a>
  <a href="https://github.com/sarim-hk/CS2Stats">
    <img src="https://img.shields.io/badge/CS2Stats-Plugin-red" alt="CS2Stats Plugin" />
  </a>
  <a href="https://github.com/sarim-hk/CS2StatsAPI">
    <img src="https://img.shields.io/badge/CS2Stats-API-green" alt="CS2Stats API" />
  </a>
  <a href="https://github.com/sarim-hk/CS2StatsWeb">
    <img src="https://img.shields.io/badge/CS2Stats-Web-blue" alt="CS2Stats Web" />
  </a>
  
</div>


## Feature Highlights:
* Automatic demo recording
* Built in ELO system to rank players
* Live match display
* In-depth stat tracking, per match, per round:
  *  ELO
  *  Kills, Assists, Deaths
  *  Utility Damage, Total Damage
  *  Enemies Flashed, Grenades Thrown
  *  Clutch Attempts and Clutches Won
  *  KAST
  *  Rounds Played and Matches Played

## Donation
[!["Paypal"](https://i.imgur.com/7igL5rh.png)](https://paypal.me/SHKTV)‎ ‎ ‎ ‎ [!["Steam Trade Link"](https://i.imgur.com/33ijkjI.png)](https://steamcommunity.com/tradeoffer/new/?partner=317935564&token=ZBiuL2Ge)

## Prerequisites
* [CounterStrikeSharp](https://github.com/roflmuffin/CounterStrikeSharp) installed on the game server
* MySQL Server
* Web server for hosting API

## Installation
* Clone the repository
* Rename the `config_template.json` within `/instance/` to `config.json`
* Fill out MySQL Server details within the newly-renamed `config.json`
* Host the Flask app as you wish - I recommend this tutorial: <https://youtu.be/KWIIPKbdxD0>
* Host the scheduler as you wish - I made a [service](https://gist.github.com/sarim-hk/b75d5d5fe427175baaa2e0f33e1ae468) for this
* Done!
