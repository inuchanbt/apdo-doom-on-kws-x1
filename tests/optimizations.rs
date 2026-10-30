// SPDX-License-Identifier: GPL-2.0-or-later
#[path = "../overlays/firmware/codec.rs"] mod codec;
#[path = "../overlays/firmware/page_cache.rs"] mod page_cache;
#[path = "../overlays/firmware/pinned_assets.rs"] mod pinned_assets;
fn word(data:&[u8], at:&mut usize) -> u32 {
    let n=u32::from_le_bytes(data[*at..*at+4].try_into().unwrap()); *at+=4; n
}
fn vectors() -> (Vec<usize>,Vec<u8>) {
    let data=std::fs::read("artifacts/codec-vectors.bin").unwrap();
    let mut at=0;
    let count=word(&data,&mut at);
    let mut sizes=Vec::new();
    for _ in 0..count {
        let len=u16::from_le_bytes(data[at..at+2].try_into().unwrap()) as usize; at+=2;
        let mut raw=[0;1024];
        codec::decode(&data[at..at+len],&mut raw).unwrap();
        at+=len;
        assert_eq!(raw,&data[at..at+1024]); at+=1024;
        sizes.push(len);
    }
    assert_eq!(at,data.len());
    (sizes,data)
}
#[test]
fn every_freedoom_page_matches_after_cross_language_compression() { vectors(); }
#[test]
fn real_engine_trace_with_compressed_cache() {
    let (sizes,_) = vectors();
    let trace=std::fs::read("artifacts/cache-traces.bin").unwrap();
    let mut at=0;
    let frames=word(&trace,&mut at);
    let mut cache=page_cache::Cache::new();
    let mut current=u32::MAX;
    let (mut total_misses,mut total_bytes)=(0usize,0usize);
    let mut frequency=vec![0usize;sizes.len()];
    let mut output=String::from("[\n");
    for frame in 0..frames {
        let reads=word(&trace,&mut at);
        let (mut misses,mut bytes)=(0usize,0usize);
        for _ in 0..reads {
            let address=word(&trace,&mut at);
            let count=word(&trace,&mut at);
            if count==0 {continue;}
            for page in address/1024..=(address+count-1)/1024 {
                if current==page {continue;}
                if cache.get(page).is_none() {
                    let len=sizes[page as usize];
                    cache.insert(page,len);
                    misses+=1; bytes+=len;
                    if frame>=2 { frequency[page as usize]+=1; }
                }
                current=page;
            }
        }
        if frame>=2 { total_misses+=misses;total_bytes+=bytes; }
        output+=&format!("  {{\"frame\":{frame},\"misses\":{misses},\"bytes\":{bytes}}}{}\n",if frame+1==frames {""} else {","});
    }
    output+="]\n";
    std::fs::write("artifacts/compressed-cache-profile.json",output).unwrap();
    std::fs::write("artifacts/page-miss-frequency.json",format!("{:?}\n",frequency)).unwrap();
    let count=(frames-2) as usize;
    println!("Compressed cache: {} roundtrips, {} wire bytes per frame",total_misses/count,total_bytes/count);
    // The old 8 KiB FIFO averaged 917 reads and 939101 raw bytes on this trace.
    assert!(total_misses/count < 550);
    assert!(total_bytes/count < 400_000);
}
#[test]
fn real_engine_trace_with_pinned_assets() {
    let (sizes,data)=vectors();
    // Verify every pinned compressed block against the independently generated
    // Python/Rust vectors before using its hit count in the replay.
    let mut pos=4;
    for page in 0..sizes.len() {
        let len=u16::from_le_bytes(data[pos..pos+2].try_into().unwrap()) as usize;
        pos+=2;
        if let Some(block)=pinned_assets::get(page as u32*1024) {
            assert_eq!(block,&data[pos..pos+len]);
        }
        pos+=len+1024;
    }
    let trace=std::fs::read("artifacts/cache-traces.bin").unwrap();
    let mut at=0;
    let frames=word(&trace,&mut at);
    let mut cache=page_cache::Cache::new();
    let mut current=u32::MAX;
    let (mut total_misses,mut total_bytes)=(0usize,0usize);
    let mut output=String::from("[\n");
    for frame in 0..frames {
        let reads=word(&trace,&mut at);
        let (mut misses,mut bytes)=(0usize,0usize);
        for _ in 0..reads {
            let address=word(&trace,&mut at);
            let count=word(&trace,&mut at);
            if count==0 {continue;}
            for page in address/1024..=(address+count-1)/1024 {
                if current==page {continue;}
                if pinned_assets::get(page*1024).is_none() && cache.get(page).is_none() {
                    let len=sizes[page as usize];
                    cache.insert(page,len);
                    misses+=1; bytes+=len;
                }
                current=page;
            }
        }
        if frame>=2 {total_misses+=misses;total_bytes+=bytes;}
        output+=&format!("  {{\"frame\":{frame},\"misses\":{misses},\"bytes\":{bytes}}}{}\n",if frame+1==frames {""} else {","});
    }
    output+="]\n";
    std::fs::write("artifacts/pinned-cache-profile.json",output).unwrap();
    let count=(frames-2) as usize;
    println!("Pinned assets: {} roundtrips, {} wire bytes per frame",total_misses/count,total_bytes/count);
    assert!(total_misses/count<250);
}
