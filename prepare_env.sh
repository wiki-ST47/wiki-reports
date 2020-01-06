# Create virtualenv
python -m venv venv

# Install requirements
source venv/bin/activate
pip install -r requirements.txt

# Update whois data
mkdir -p flaredata
cd flaredata
rm ./rib.*.bz2
python ../venv/bin/pyasn_util_download.py --latestv46
python ../venv/bin/pyasn_util_convert.py --single ./rib.*.bz2 ipasn.dat
python ../venv/bin/pyasn_util_asnames.py > asnames.txt
cd ..
