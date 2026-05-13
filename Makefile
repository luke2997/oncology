all:
	./run_all.sh

python:
	python programs/python/run_all.py

clean:
	rm -rf data/raw/*.csv data/adam/*.csv data/specs/*.csv data/specs/*.xml outputs/tables/* outputs/listings/* outputs/figures/* outputs/reports/* docs/*.pdf qc/*.csv qc/*.md metadata/*.csv assets/preview_*.png
