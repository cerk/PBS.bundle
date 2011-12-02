import re

PBS_PREFIX      = "/video/pbs"
CACHE_INTERVAL  = 3600 * 3
PBS_URL         = 'http://video.pbs.org/'
PAGE_SIZE  		= 12

####################################################################################################
def Start():
  Plugin.AddPrefixHandler(PBS_PREFIX, VideoMenu, 'PBS', 'icon-default.png', 'art-default.jpg')
  Plugin.AddViewGroup("Details", viewMode="InfoList", mediaType="items")
  MediaContainer.title1 = 'PBS'
  MediaContainer.content = 'Items'
  MediaContainer.art = R('art-default.jpg')
  DirectoryItem.thumb = R("icon-default.png")
  HTTP.CacheTime = CACHE_INTERVAL

####################################################################################################
def UpdateCache():
  HTTP.Request(PBS_URL)

####################################################################################################
def VideoMenu():
  dir = MediaContainer(noCache=True)
  dir.Append(Function(DirectoryItem(GetPrograms, title="All Programs"), cls='subnav hide threecol'))
  dir.Append(Function(DirectoryItem(GetPrograms, title="All Topics"), cls='subnav hide twocol', prefix="li[@class='topics-nav']/", path='li/ol/li/a/text()[normalize-space(.)]/parent::a'))
  dir.Append(Function(DirectoryItem(GetMostWatched, title="Most Watched")))  
  dir.Append(Function(InputDirectoryItem(Search, title=L("Search..."), prompt=L("Search for Videos"), thumb=S('search.png'))))
  return dir

####################################################################################################
def GetPrograms(sender, cls, prefix='', path='li/ol/li/a'):
  dir = MediaContainer(title2=sender.itemTitle)
  Log("//%sul[@class='%s']/%s" % (prefix, cls, path))
  for program in HTML.ElementFromURL(PBS_URL).xpath("//%sul[@class='%s']/%s" % (prefix, cls, path)):
    url = program.get('href')
    dir.Append(Function(DirectoryItem(GetEpisodes, title=program.text), pid=url))
  return dir
  
####################################################################################################
def GetMostWatched(sender):
  dir = MediaContainer(title2=sender.itemTitle)
  for show in HTML.ElementFromURL(PBS_URL).xpath('//div[@id="most-watched-videos"]//li'):
    title = show.xpath('.//span[@class="title clear clearfix"]/a')[0].text
    subtitle = show.xpath('.//span[@class="description"]')[0].text.strip()
    summary = ''
    thumb = show.xpath('.//img')[0].get('src')
    href = show.xpath('.//div/a')[0].get('href')
    sid = href.split('/')[-2]
    dir.Append(Function(VideoItem(PlayVideo, title, subtitle, summary, None, thumb), sid=sid))
  return dir
  
####################################################################################################
def GetEpisodes(sender, pid, page=1):
  dir = MediaContainer(viewGroup='Details', title2=sender.itemTitle)
  url = pid
  data = HTML.ElementFromURL(url)
  for episode in data.xpath('//div[@id="fullepisodes"]//div[@class="videobox "]'):
     title = episode.xpath('.//h2[@class="title"]')[0].text
     try: subtitle = episode.xpath('.//span[@class="airdate"]')[0].text
     except: subtitle = ''
     summary = episode.xpath('.//span[@class="description"]')[0].text
     duration = episode.xpath('.//span[@class="duration"]')[0].text
     duration = [int(d) for d in duration.split(':')]
     if len(duration) == 3:
        duration = duration[0]*3600+duration[1]*60+duration[2]
     else:
        duration = duration[0]*60+duration[1]
     duration = duration * 1000
     thumb = episode.xpath('.//img[@class="thumbnail"]')[0].get('src')
     sid = episode.xpath('.//input[@class="contentID"]')[0].get('value')
     dir.Append(Function(VideoItem(PlayVideo, title, subtitle, summary, duration, thumb), sid=sid))
  return dir
  
####################################################################################################
def Search(sender, query, page=1):
  dir = MediaContainer(viewGroup='Details', title2='Search Results', replaceParent=(page>1))
  query = query.replace(' ', '+')
  data = HTML.ElementFromURL('http://www.pbs.org/search/?q=%s&mediatype=Video&start=%d' % (query, (int(page)-1)*10))
  for show in data.xpath('//div[@class="ez-mod ez-itemMod ez-mainSearch ez-col-1"]//li'):
    try:
      show_title = ''.join(show.xpath('.//p[@class="ez-metaextra1 ez-icon"]//text()'))
      ep_title = ''.join(show.xpath('.//a[@class="ez-title"]//text()'))
      title = '%s | %s' % (show_title, ep_title) 
      summary = ''.join(show.xpath('.//p[@class="ez-desc"]//text()'))
      thumb = show.xpath('.//img[@class="ez-primaryThumb"]')[0].get('src')
      sid = show.xpath('.//a[@class="ez-title"]')[0].get('href').split('/')[-1]
      dir.Append(Function(VideoItem(PlayVideo, title, summary=summary, thumb=thumb), sid=sid))
    except:
      pass
  if len(data.xpath('//a[@title="Next Result Page"]')) != 0:
    dir.Append(Function(DirectoryItem(Search, title="More results"), query=query, page=page+1))
  return dir

####################################################################################################
def ExtractReleaseUrlNative(releaseUrl):
	Log("ReleaseURL:"+releaseUrl)
	tokens = releaseUrl.split('$')
	decrypted = Helper.Run('decrypt', tokens[1] + "#" + tokens[2])
	decrypted = decrypted + "&format=SMIL"
	Log("Decrypted URL:"+decrypted)
	return decrypted

####################################################################################################
def PlayVideo(sender, sid):
  url = PBS_URL + 'videoPlayerInfo/%s' % sid
  
  xml = HTTP.Request(url, cacheTime=0).content
  #xml = String.Unquote(xml, False)
  start = 12 + xml.find('<releaseURL>')
  end = xml.find('</releaseURL>')
  release = xml[start:end]
  releaseUrl = ExtractReleaseUrlNative(release)
  NS = {"ns":"http://www.w3.org/2001/SMIL20/Language", "tp":"http://xml.theplatform.com/mps/metadata/content/custom"}
  xml = XML.ElementFromURL(releaseUrl, cacheTime=0)
  player = xml.xpath('/ns:smil/ns:head/ns:meta', namespaces=NS)[0].get('base')
  directFeed = player.find('http://') > -1
  if directFeed: 
    clip = xml.xpath('/ns:smil/ns:body//ns:ref', namespaces=NS)[0].get('src')
  else: 
    clip = 'mp4:'+xml.xpath('/ns:smil/ns:body//ns:ref', namespaces=NS)[0].get('src').replace('.mp4','')
  return Redirect(RTMPVideoItem(player, clip))
  