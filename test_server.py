import datetime as dt, unittest, tempfile, pathlib, json
from unittest.mock import patch
import server as s
class Tests(unittest.TestCase):
 def feed(self,cat='Technology',**kw):return dict(category=cat,source='Fixture',url='https://example.com/feed',include_images=True,include_description=True,enabled=True,**kw)
 def test_rss(self):
  xml=b'''<rss xmlns:media="http://search.yahoo.com/mrss/"><channel><item><title>A &amp; B</title><link>https://example.com/story?utm_source=rss</link><description><![CDATA[<p>Text only</p><script>hidden</script>]]></description><media:content url="https://example.com/p.jpg" width="900" medium="image"><media:credit>Photographer</media:credit></media:content></item></channel></rss>'''
  r=s.parse(xml,self.feed())[0];self.assertEqual(r['title'],'A & B');self.assertEqual(r['link'],'https://example.com/story');self.assertEqual(r['description'],'Text only');self.assertEqual(r['credit'],'Photographer');self.assertEqual(r['image'],'https://example.com/p.jpg')
  f=self.feed();f['include_images']=False;f['include_description']=False;r=s.parse(xml,f)[0];self.assertFalse(r['image']);self.assertFalse(r['description'])
 def test_atom(self):
  xml=b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Atom story</title><link rel="self" href="https://example.com/feed"/><link href="https://example.com/story"/><summary>Hi</summary></entry></feed>'
  self.assertEqual(s.parse(xml,self.feed())[0]['link'],'https://example.com/story')
 def test_xml_reject(self):
  with self.assertRaises(ValueError):s.parse(b'<!DOCTYPE rss><rss/>',self.feed())
 def test_rotate(self):
  def r(i,c,title=None):return dict(id=str(i),category=c,title=title or str(i),date='')
  a,b=s.CATS[:2];rows=s.round_robin([[r(1,a),r(2,a),r(3,a)],[r(1,b),r(4,b),r(5,b)]],2);self.assertEqual([x['id'] for x in rows],['1','4','2','5'])
 def test_cache(self):
  f=self.feed();r=dict(id='a',category=f['category'],title='Story',date='',description='text',image='https://example.com/p.jpg',credit='Photo',source=f['source']);cfg=dict(feeds=[f]);
  with tempfile.TemporaryDirectory() as d:
   conf=pathlib.Path(d)/'settings.json';cache=pathlib.Path(d)/'cache.json';conf.write_text(json.dumps(cfg))
   with patch.object(s,'CONFIG',conf),patch.object(s,'CACHE',cache),patch.object(s,'fetch',return_value=[r]):s.cycle();self.assertEqual(s.STATE['mode'],'live');self.assertFalse(s.STATE['stale'])
   f['include_images']=False;conf.write_text(json.dumps(cfg))
   with patch.object(s,'CONFIG',conf),patch.object(s,'CACHE',cache),patch.object(s,'fetch',side_effect=TimeoutError('test outage')):s.cycle();self.assertTrue(s.STATE['stale']);self.assertEqual(s.STATE['items'][0]['title'],'Story');self.assertFalse(s.STATE['items'][0]['image']);conf.write_text(json.dumps(dict(feeds=[])));s.cycle();self.assertEqual(s.STATE['mode'],'demo');self.assertFalse(s.STATE['items'])
if __name__=='__main__':unittest.main()
