function redirectOrUpdateVisible(){rawHash=$(location).attr("hash").replace(/^#/,""),rawHash?("undefined"==typeof oldVisible&&(oldVisible="AußenstelleBrigittenauI"),decodedHash=decodeURIComponent(rawHash),oldVisibleMenuItem=".navbar-start a:contains("+oldVisible+")",$(oldVisibleMenuItem).hasClass("activeMenuItem")&&$(oldVisibleMenuItem).removeClass("activeMenuItem"),activeMenuItem=".navbar-start a:contains("+decodedHash+")",$(activeMenuItem).addClass("activeMenuItem"),oldVisibleItemList="#"+oldVisible,$(oldVisibleItemList).hasClass("show")&&$(oldVisibleItemList).removeClass("show"),activeItemList="#"+decodedHash,$(activeItemList).addClass("show"),oldVisible=decodedHash,window.scrollTo(0,0)):(location.href="#AußenstelleBrigittenauI",oldVisible="AußenstelleBrigittenauI")}