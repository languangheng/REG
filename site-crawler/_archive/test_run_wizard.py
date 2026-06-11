"""Test run_wizard with real mimimi.top site."""
import sys
sys.path.insert(0, r"C:\Users\languangheng\.qclaw\workspace-tfxjjhfnjialcuju\site-crawler")

from crawler.config_wizard import run_wizard

run_wizard(
    key="mimimi",
    name="Mimimi",
    base_url="https://www.mimimi.top",
    entry_url="https://www.mimimi.top/vodshow/12-----------.html",
)
