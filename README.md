# alertmagnet

Reduce the overall alert count by judging alerts in dependency with their peers in history.

## Project Setup

1. Download and checkout the git project

```bash
git clone https://github.com/sapcc/alertmagnet
```

2. Setup virtual environment

```bash
python3 -m venv .venv/
```

3. Activate the `.venv`

```bash
. .venv/bin/activate
```

4. Install dependencies

```bash
pip install -r requirements.txt
```

5. Adjust the config file

> For further info see [Config File Information](#config-file-information)

6. Run the program

```bash
python main.py
```

## Config File Information

> [!NOTE]
> To change the location of your config file set an environment variable with the name `ALERTMAGNET_CONFIG_FILE`

> The default config file is located under `config/settings.conf`. There you have a section `[AlertMagnet]`. All config settings have to be done beneath this section. In the following table are the possbile config settings listed.

| setting               | datatype | description                                                                                                                                                  | default / [example value]                    |
| --------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------- |
| api_endpoint          | str      | API endpoint to send the query against                                                                                                                       | [https://www.metrics.region.app.com/api/v1/] |
| cert                  | str      | Relative path to a certificate if necessary for the endpoint                                                                                                 | [./certificates/certificate.pem]             |
| timeout               | int      | Number of seconds the client will wait for the server to send a response                                                                                     | 30                                           |
| directory_path        | str      | Directory path in which the query results are stored                                                                                                         | [./data/query_results]                       |
| threshold             | int      | Threshold in days which specifies when the data are interpolated by Thanos <br> This helps splitting the queries due to efficiency and resource optimization | 90                                           |
| delay                 | float    | Delay in seconds between each query execution                                                                                                                | 0.25                                         |
| threads               | int      | Maximum number of threads to use for query execution                                                                                                         | 12                                           |
| max_long_term_storage | str      | Maximum long term storage following the format <a>y, <b>m, <c>w, <d>d                                                                                        | 1y                                           |
| log_to_file           | bool     | Toggle which defines whether logs are written into a file.                                                                                                   | False                                        |
| log_level             | str      | Log Level -> valid values are \| CRITICAL \| ERROR \| WARNING \| INFO \| DEBUG \|                                                                            | INFO                                         |

> [!NOTE]
> When you decide to use `log_level=DEBUG` only query for short time ranges
