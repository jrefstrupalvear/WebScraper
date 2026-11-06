# La Liga Player Performance Webscraper

## Overview
This is a La Liga Player Performance Webscraper that scrapes data from FotMob for player performance over the 2025-2026 season.
While FotMob does provide an API, in the spirit of the web scraping assignment, I used the JSON that is embedded in the HTML to 
find the player data. Functions and docstrings model the style of those used in class. A player must have played 10 games for
their average to be considered.

## Usage
Install the requirements:

```bash
pip install -r requirements.txt
```

Run the scraper:

```bash
./scraper.py [-t TEAM -w WORKERS]
```

| Flag | Description | Default |
|---|---|---|
| `-t TEAM` | LaLiga team to look up | `barcelona` |
| `-w WORKERS` | Number of concurrent downloads | `4` |
| `-h` | Show the help message | |

Example:

```bash
./scraper.py -t "Real Madrid" -w 10
```

Team names are listed in `teams.txt`. Part of a name works if it matches only one team, and accents are optional.

## Performance
### Functional Programming

The scraper uses `map`, `filter`, and `lambda` to process games and ratings in small functions. This had no noticeable effect on speed because most of the runtime is spent waiting on the network, but it kept the code simple and easy to run across threads.

### Concurrency

The scraper uses `ThreadPoolExecutor` to download match pages at the same time. 

### Results

**By default, 4 workers are enabled**
To use this program sequentially, use the -w 1 tag for only 1 worker
Performance with 1,5, and 10 workers
<img width="1971" height="2000" alt="image" src="https://github.com/user-attachments/assets/46bb79e0-4edb-4216-ac9d-7da76c948f89" />

| Workers | Time | Speedup vs 1 worker |
|---|---|---|
| 1 | 5.1s | Baseline |
| 5 | 2.8s | 1.8 |
| 10 | 1.5s | 3.4 |
