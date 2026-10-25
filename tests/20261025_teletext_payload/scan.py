"""Read-only packet evidence for the recording currently under investigation."""
import collections
import json
import os
import time

PATH='/media/usb/Filme/20260812 2012 - Sky Cinema Action - Gesetz der Rache.ts'
PID=34  # From the observed native subtitle inventory for this recording only.


def hamming_nibble(value):
    # ETSI teletext Hamming(8,4) data bit positions, no error correction claimed.
    return ((value & 1) << 3) | (value & 4) | ((value >> 3) & 2) | ((value >> 6) & 1)


def text_character(value):
    return int('{:08b}'.format(value)[::-1],2) & 127


class Evidence:
    def __init__(self):
        self.counts=collections.Counter()
        self.units=collections.Counter()
        self.pages={}
        self.current={}
        self.pes=bytearray()
        self.expected=None
        self.last_cc=None

    def parse_pes(self, data):
        if len(data)<10 or data[:4]!=b'\x00\x00\x01\xbd':
            return
        self.counts['private_pes']+=1
        header=9+data[8]
        if header>=len(data) or not 0x10<=data[header]<=0x1f:
            return
        self.counts['teletext_pes']+=1
        offset=header+1
        while offset+2<=len(data):
            kind,length=data[offset:offset+2];offset+=2
            if kind==255 or offset+length>len(data):break
            unit=data[offset:offset+length];offset+=length
            self.units[kind]+=1
            if kind not in (2,3) or length!=44 or unit[1]!=0xe4:continue
            self.counts['teletext_units']+=1
            address=hamming_nibble(unit[2]) | hamming_nibble(unit[3])<<4
            magazine=(address&7) or 8;row=address>>3;payload=unit[4:44]
            if row==0:
                page=hamming_nibble(payload[0]) | hamming_nibble(payload[1])<<4
                if page==255:
                    self.current.pop(magazine,None);continue
                key=(magazine,page)
                stats=self.pages.setdefault(key,dict(headers=0,rows_with_text=0,subtitle_flag_headers=0))
                stats['headers']+=1
                stats['subtitle_flag_headers']+=bool(hamming_nibble(payload[5])&8)
                self.current[magazine]=key
            elif 1<=row<=23 and magazine in self.current:
                # Count nonblank rows; never output film dialogue text.
                if any(32<text_character(char)<127 for char in payload):
                    self.pages[self.current[magazine]]['rows_with_text']+=1

    def flush(self):
        if self.pes:
            self.parse_pes(bytes(self.pes))
        self.pes.clear();self.expected=None

    def packet(self,p):
        if len(p)!=188 or p[0]!=71:
            self.counts['bad_sync']+=1;return
        pid=((p[1]&31)<<8)|p[2]
        if pid!=PID:return
        self.counts['pid_packets']+=1
        if p[1]&128:
            self.counts['transport_errors']+=1;self.pes.clear();self.expected=None;return
        if (p[3]>>6)&3:
            self.counts['scrambled_packets']+=1;self.pes.clear();self.expected=None;return
        adaptation=(p[3]>>4)&3
        if adaptation not in (1,3):return
        offset=4 if adaptation==1 else 5+p[4]
        if offset>=188:return
        self.counts['clear_payload_packets']+=1
        cc=p[3]&15
        if self.last_cc==cc:
            self.counts['duplicate_packets']+=1;return
        if self.last_cc is not None and cc!=((self.last_cc+1)&15):
            self.counts['continuity_gaps']+=1;self.pes.clear();self.expected=None
        self.last_cc=cc
        payload=p[offset:]
        if p[1]&64:
            self.flush()
            if payload[:3]!=b'\x00\x00\x01':return
            self.pes.extend(payload)
            if len(self.pes)>=6:
                length=int.from_bytes(self.pes[4:6],'big')
                self.expected=length+6 if length else None
        elif self.pes:
            self.pes.extend(payload)
        if self.expected is not None and len(self.pes)>=self.expected:
            self.parse_pes(bytes(self.pes[:self.expected]));self.pes.clear();self.expected=None
        elif len(self.pes)>1048576:
            self.counts['oversize_pes']+=1;self.pes.clear();self.expected=None

    def report(self):
        pages=[]
        for (magazine,page),stats in sorted(self.pages.items()):
            pages.append(dict(magazine=magazine,page_bcd='%02x'%page,
                              display_page='%d%02x'%(magazine,page),**stats))
        counts={key:self.counts[key] for key in ('pid_packets','clear_payload_packets','scrambled_packets','teletext_pes','teletext_units','transport_errors','continuity_gaps')}
        counts.update(self.counts)
        return dict(pid=PID,counts=counts,data_unit_ids={hex(k):v for k,v in self.units.items()},pages=pages)


def detect(data):
    for stride in (188,192,204):
        for offset in range(min(stride,len(data))):
            if all(offset+i*stride<len(data) and data[offset+i*stride]==71 for i in range(6)):
                return stride,offset
    raise ValueError('Kein sicherer TS-Paketabstand erkannt')


def scan(path,limit=1073741824,seconds=50):
    before=os.stat(path);evidence=Evidence();started=time.monotonic();read=0
    with open(path,'rb') as handle:
        stride,offset=detect(handle.read(204*8))
        handle.seek(offset);read=offset;next_progress=134217728
        while read<before.st_size and read<limit and time.monotonic()-started<seconds:
            block=handle.read(min(stride*32768,limit-read))
            if not block:break
            for index in range(0,len(block)-187,stride):evidence.packet(block[index:index+188])
            read+=len(block)
            if read>=next_progress:
                print('GELESEN: %d MiB'%(read//1048576),flush=True);next_progress+=134217728
        evidence.flush()
    after=os.stat(path)
    result=evidence.report()
    result.update(bytes_read=read,file_size=before.st_size,complete=read>=before.st_size,
                  file_unchanged=(before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns),
                  packet_size=stride,elapsed_seconds=round(time.monotonic()-started,2))
    return result


def main():
    print('VIDEOTEXT-DATENTEST: Gesetz der Rache, PID 34 aus dem Untertitellog.',flush=True)
    print('Nur Datei lesen. Kein Plugin-Umbau, kein Neustart, keine Wiedergabesteuerung.',flush=True)
    if not os.path.isfile(PATH):raise SystemExit('Originalaufnahme nicht gefunden. Nichts geaendert.')
    print(json.dumps(scan(PATH),ensure_ascii=True,indent=2),flush=True)
    print('FERTIG. Originaldatei und Einstellungen unveraendert.',flush=True)

if __name__=='__main__':main()
