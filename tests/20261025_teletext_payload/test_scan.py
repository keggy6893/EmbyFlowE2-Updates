import unittest,tempfile
from pathlib import Path
from scan import Evidence,detect,scan,hamming_nibble
# Construct valid encoded bit positions for each nibble. We test the standard
# field extraction, not error correction or a complete teletext text decoder.
def ham(n):return ((n&8)>>3)|(n&4)|((n&2)<<3)|((n&1)<<6)
def reverse(char):return int('{:08b}'.format(ord(char))[::-1],2)
def unit(mag,row,page=None,text=False):
 address=(mag&7)|(row<<3);data=bytearray(40)
 if row==0:data[0]=ham(page&15);data[1]=ham(page>>4);data[5]=ham(8)
 if text:data[0:3]=bytes(reverse(c) for c in 'ABC')
 raw=bytes([0,0xe4,ham(address&15),ham(address>>4)])+bytes(data)
 return bytes([3,len(raw)])+raw
def pes(body):
 data=b'\x80\x00\x00'+bytes([0x10])+body
 return b'\x00\x00\x01\xbd'+len(data).to_bytes(2,'big')+data
def packets(data,pid=34):
 out=[];cc=0
 while data:
  chunk,data=data[:184],data[184:]
  out.append(bytes([71,((pid>>8)&31)|(64 if cc==0 else 0),pid&255,16|(cc&15)])+chunk+b'\xff'*(184-len(chunk)));cc+=1
 return out
class Tests(unittest.TestCase):
 def test_hamming_bits(self):
  for n in range(16):self.assertEqual(hamming_nibble(ham(n)),n)
 def test_dynamic_pages_and_text_rows(self):
  e=Evidence()
  for p in packets(pes(unit(7,0,0x77)+unit(7,1,text=True)+unit(7,0,0x78)+unit(7,2,text=True))):e.packet(p)
  e.flush();r=e.report();self.assertEqual([x['display_page'] for x in r['pages']],['777','778']);self.assertEqual([x['rows_with_text'] for x in r['pages']],[1,1]);self.assertEqual(r['counts']['teletext_pes'],1)
 def test_different_pages_not_hardcoded(self):
  e=Evidence();e.parse_pes(pes(unit(2,0,0x34)));self.assertEqual(e.report()['pages'][0]['display_page'],'234')
 def test_missing_pid(self):
  e=Evidence()
  for p in packets(pes(unit(7,0,0x77)),pid=256):e.packet(p)
  self.assertEqual(e.report()['pages'],[]);self.assertEqual(e.report()['counts']['pid_packets'],0)
 def test_scrambled_not_decoded(self):
  e=Evidence();p=bytearray(packets(pes(unit(7,0,0x77)))[0]);p[3]|=128;e.packet(p);self.assertEqual(e.counts['scrambled_packets'],1);self.assertEqual(e.report()['pages'],[])
 def test_transport_error_not_decoded(self):
  e=Evidence();p=bytearray(packets(pes(unit(7,0,0x77)))[0]);p[1]|=128;e.packet(p);self.assertEqual(e.counts['transport_errors'],1);self.assertEqual(e.report()['pages'],[])
 def test_bad_lengths_safe(self):
  e=Evidence()
  for data in (b'',b'bad',pes(b'\x03\xffshort'),pes(b'\xff\xff')):e.parse_pes(data)
  self.assertEqual(e.report()['pages'],[])
 def test_packet_alignment(self):
  p=packets(pes(unit(7,0,0x77)))[0]
  for size,prefix,suffix in ((188,b'',b''),(192,b'1234',b''),(204,b'',b'0'*16)):
   self.assertEqual(detect((prefix+p+suffix)*8),(size,len(prefix)))
 def test_unknown_format_rejected(self):
  with self.assertRaises(ValueError):detect(b'not a TS stream'*200)
 def test_full_scan_preserves_file(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'recording.ts';data=b''.join(packets(pes(unit(7,0,0x77)+unit(7,1,text=True))))
   null=bytes([71,31,255,16])+b'\xff'*184;data+=null*10;p.write_bytes(data)
   result=scan(p);self.assertTrue(result['complete']);self.assertTrue(result['file_unchanged']);self.assertEqual(p.read_bytes(),data);self.assertEqual(result['pages'][0]['rows_with_text'],1)
 def test_empty_page_is_not_claimed_text(self):
  e=Evidence();e.parse_pes(pes(unit(7,0,0x77)+unit(7,1)));self.assertEqual(e.report()['pages'][0]['rows_with_text'],0)
 def test_known_hamming_wire_vectors(self):
  canonical=(0x15,0x02,0x49,0x5e,0x64,0x73,0x38,0x2f,0xd0,0xc7,0x8c,0x9b,0xa1,0xb6,0xfd,0xea)
  for nibble,value in enumerate(canonical):
   wire=int('{:08b}'.format(value)[::-1],2);self.assertEqual(hamming_nibble(wire),nibble)
 def test_multi_packet_pes_reassembled(self):
  e=Evidence();data=pes(unit(7,0,0x77)+b''.join(unit(7,row,text=True) for row in range(1,20)))
  for p in packets(data):e.packet(p)
  e.flush();self.assertEqual(e.report()['pages'][0]['rows_with_text'],19)
 def test_adaptation_field_payload(self):
  data=pes(unit(7,0,0x77));adapt=183-len(data)
  packet=bytes([71,64,34,48,adapt])+b'\x00'*adapt+data
  self.assertEqual(len(packet),188);e=Evidence();e.packet(packet);e.flush();self.assertEqual(e.report()['pages'][0]['display_page'],'777')
 def test_duplicate_packet_not_decoded_twice(self):
  p=packets(pes(unit(7,0,0x77)))[0];e=Evidence();e.packet(p);e.packet(p);e.flush();self.assertEqual(e.report()['pages'][0]['headers'],1);self.assertEqual(e.counts['duplicate_packets'],1)
 def test_continuity_gap_drops_incomplete_pes(self):
  data=pes(unit(7,0,0x77)+b''.join(unit(7,row,text=True) for row in range(1,20)));parts=packets(data)
  e=Evidence();e.packet(parts[0]);e.packet(parts[2]);e.flush();self.assertEqual(e.counts['continuity_gaps'],1);self.assertEqual(e.report()['pages'],[])
if __name__=='__main__':unittest.main()
