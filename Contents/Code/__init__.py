import re

PBS_PREFIX      = "/video/pbs"
CACHE_INTERVAL  = 3600 * 3
PBS_URL         = 'http://video.pbs.org/'
PAGE_SIZE  		= 12

####################################################################################################
def Start():
  Plugin.AddPrefixHandler(PBS_PREFIX, MainMenu, 'PBS', 'icon-default.png', 'art-default.jpg')
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
def MainMenu():
  dir = MediaContainer()
  dir.Append(Function(DirectoryItem(GetPrograms, title="All Programs"), cls='subnav hide threecol'))
  dir.Append(Function(DirectoryItem(GetCollectionPrograms, title="All Topics"), cls='subnav hide twocol', category='subject', prefix="li[@class='topics-nav']/", path='li/ol/li/a'))
  dir.Append(Function(DirectoryItem(GetCollectionPrograms, title="All Collections"), cls='subnav hide twocol', category='feature', prefix="li[@class='collections-nav']/", path='li/ol/li/a'))
  dir.Append(Function(DirectoryItem(GetShorties, title="Most Watched"), name='mostWatched'))  
  dir.Append(Function(InputDirectoryItem(Search, title=L("Search..."), prompt=L("Search for Videos"), thumb=R('search.png'))))
  return dir

####################################################################################################
def GetPrograms(sender, cls, prefix='', path='li/ol/li/a'):
  dir = MediaContainer(title2=sender.itemTitle)
  Log("//%sul[@class='%s']/%s" % (prefix, cls, path))
  for program in HTML.ElementFromURL(PBS_URL).xpath("//%sul[@class='%s']/%s" % (prefix, cls, path)):
    pid = re.findall('[0-9]+', program.get('href'))[0]
    Log("PID:"+pid+":"+program.text)
    dir.Append(Function(DirectoryItem(GetEpisodes, title=program.text), pid=pid))
  return dir
  
####################################################################################################
def GetCollectionPrograms(sender, cls, category, prefix='', path='li/ol/li/a'):
  dir = MediaContainer(title2=sender.itemTitle)
  Log("//%sul[@class='%s']/%s" % (prefix, cls, path))
  for program in HTML.ElementFromURL(PBS_URL).xpath("//%sul[@class='%s']/%s" % (prefix, cls, path)):
    pid = re.findall('[0-9]+', program.get('href'))[0]
    Log("PID:"+pid+":"+program.text)
    dir.Append(Function(DirectoryItem(GetProgram, title=program.text), pid=pid, category=category))
  return dir

####################################################################################################
def GetShorties(sender, name):
  dir = MediaContainer(title2=sender.itemTitle)
  for show in HTML.ElementFromURL('http://www.pbs.org/video/%s/PBS/' % name).xpath('//li'):
    title = show.xpath('div/a')[0].get('title')
    subtitle = show.xpath('div/span/a')[0].text
    summary = ''
    thumb = show.xpath('div/a/span[@class="video-thumbnail"]/img')[0].get('src')
    href = show.xpath('div/a')[0].get('href')
    sid = href.split('/')[-2]
    dir.Append(Function(VideoItem(PlayVideo, title, subtitle, summary, None, thumb), sid=sid))
  return dir
  
####################################################################################################
def GetProgram(sender, pid, category, start=0):
  url = PBS_URL + '%s/%s/start/1/end/99' % (category, pid)
  Log("URL:"+url)
  timeoutCount = 0
  while timeoutCount < 5:
	  try:
	      dir = MediaContainer(viewGroup='Details', title2=sender.itemTitle)
	      for show in HTML.ElementFromURL(url).xpath('//dl'):
	        dir.Append(ParseVideo(sender.itemTitle, show))
	      return dir
	  except Ex.URLError, error:
	      timeoutCount = timeoutCount + 1
	      Log("Timeout Count:"+str(timeoutCount))

  Log.Error("Error accessing "+url + ":" + str(error))
  return MessageContainer("PBS","Error accessing server: "+str(error)+ ". Please try again.")

####################################################################################################
def GetEpisodes(sender, pid, page=1):
  url = PBS_URL + 'programEpisodes/%s/start/%d/end/%d' % (pid, page, page+PAGE_SIZE)
  Log("URL:"+url)
  dir = MediaContainer(viewGroup='Details', title2=sender.itemTitle)
  content = JSON.ObjectFromURL(url)
  for episode in content:
     title = episode['title']
     subtitle = "Aired "+episode['airdate']
     summary = episode['short_description']
     duration = episode['duration']
     duration = [int(d) for d in duration.split(':')]
     if len(duration) == 3:
        duration = duration[0]*3600+duration[1]*60+duration[2]
     else:
        duration = duration[0]*60+duration[1]
     duration = duration * 1000
     thumb = episode['thumbnail_url']
     sid = episode['contentID']
     dir.Append(Function(VideoItem(PlayVideo, title, subtitle, summary, duration, thumb), sid=sid))
  if len(content) == PAGE_SIZE:
     dir.Append(Function(DirectoryItem(GetEpisodes, title="More ..."), pid=pid, page=page+PAGE_SIZE))
  return dir

  
####################################################################################################
def Search(sender, query, page=1):
  dir = MediaContainer(viewGroup='Details', title2='Search Results', replaceParent=(page>1))
  query = query.replace(' ', '+')
  for show in HTML.ElementFromURL(PBS_URL + 'searchForm/?q=%s' % (query)).xpath('//dl'):
    dir.Append(ParseVideo('', show))
  return dir

####################################################################################################
def ParseVideo(show_title, show):
  title = show.xpath('dd/p/a')[0].text
  title = title.strip()
  
  if len(show_title):
    title = title.replace(show_title, '').replace('|','').strip()
  
  summary = show.xpath('dd/p/span[@class="list"]')[0].text
  thumb = show.xpath('dt/img')[0].get('src')
  sid = re.findall('/[0-9]+/', show.xpath('dt/a[@class="play"]')[0].get('href'))[0][1:-1] 
  duration = show.xpath('dd/p/span[@class="time"]')[0].text.replace('(','').replace(')','')
  duration = [int(d) for d in duration.split(':')]
  if len(duration) == 3:
    duration = duration[0]*3600+duration[1]*60+duration[2]
  else:
    duration = duration[0]*60+duration[1]
  duration = duration * 1000
  subtitle = [e.strip() for e in show.xpath('dd/ul/li[@class="info"]/p')[0].itertext()][1]
  return Function(VideoItem(PlayVideo, title, subtitle, summary, duration, thumb), sid=sid)

	
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
    #player = "http://www-tc.pbs.org/cove-ingest/"
    #clip = "errormessages/Unavailable.flv"
  else: 
    clip = 'mp4:'+xml.xpath('/ns:smil/ns:body//ns:ref', namespaces=NS)[0].get('src').replace('.mp4','')
  return Redirect(RTMPVideoItem(player, clip))
  