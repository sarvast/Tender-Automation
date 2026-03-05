import re
from bs4 import BeautifulSoup

html_snippet = """<div class="card"><div class="block_header"><p class="bid_no pull-left"><span class="bid_title">BID NO: </span><a class="bid_no_hover" href="/showbidDocument/8959926" target="_blank">GEM/2026/B/7216049</a></p><p class="pull-right otherDetails" data-bid="8959926" id="other-details-8959926" onclick="getOtherDetails(8959926)"><a><i class="fa fa-arrow-circle-left"></i>  View Corrigendum/Representation</a></p></div><div class="clearfix"></div><div class="card-body"><div class="row"><div class="col-md-4"><div class="row"><strong>Items:</strong> <a data-content="Power supply for vidar scanner,Feeder and compression roller,Drive closing cover kit for ecmo,Poten" data-original-title="Spares for monitors and scanners" data-toggle="popover" data-trigger="hover" title="">Power supply for vidar scanner...</a></div><div class="row"><strong>Quantity:</strong> 9</div></div><div class="col-md-5"><div class="row"><strong>Department Name And Address:</strong> </div><div class="row">Ministry of Science and Technology<br/>Department of Science and Technology (DST)</div></div><div class="col-md-3"><div class="row"><strong>Start Date:</strong> <span class="start_date">12-02-2026 9:48 AM</span></div><div class="row"><strong>End Date:</strong>   <span class="end_date">05-03-2026 10:00 AM</span></div></div><div class="clearfix"></div></div></div></div>"""

soup = BeautifulSoup(html_snippet, "html.parser")
card = soup.select_one(".card")
card_text = card.get_text(separator=" ", strip=True)

print("CARD TEXT:", card_text)

qty_match = re.search(r"Quantity:\s*(\d+)", card_text, re.IGNORECASE)
print("REGEX MATCH:", qty_match)

if qty_match:
    print("QUANTITY:", int(qty_match.group(1)))
else:
    print("NO MATCH")
