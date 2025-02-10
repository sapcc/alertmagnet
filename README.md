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
pip install setuptools
python setup.py install
```

5. Run the program

```bash
python main.py -a "https://this/target/url/shoudl/end/with/something/like/api/v1/" -c "path_to_your_certificates_if_you_neew/certificate.pem" -p "/directory/to/store/your/query_results" -b 90 -t 150
```

Parameter explanation:

- \- a, api endpoint to query against [required]
- \- c, relative path to the certificate which is used to create the request
- \- p, directory path in which the query results are stored
- \- b, Threshold in days which specifies when the data are interpolated by Thanos This helps splitting the queries due to efficiency and resource optimization
- \- t, number of seconds the client will wait for the server to send a response \[default: 30\]

> [!TIP]
> Run the following command to get an overview about all available command line parameters
>
> ```bash
> python main.py --help
> ```
