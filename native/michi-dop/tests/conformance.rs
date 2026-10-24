//! M13 Gate A byte conformance against the shared Python golden vector.

use gstreamer as gst;
use gstreamer::prelude::*;

fn init() {
    gst::init().unwrap();
    michidop::plugin_register_static().unwrap();
}

fn run(format: &str, chunks: &[&[u8]]) -> Vec<u8> {
    run_with(format, chunks, 352_800, false)
}

fn run_with(format: &str, chunks: &[&[u8]], rate: i32, reverse: bool) -> Vec<u8> {
    init();
    let pipeline = gst::Pipeline::new();
    let src = gst::ElementFactory::make("appsrc").build().unwrap();
    let in_filter = gst::ElementFactory::make("capsfilter").build().unwrap();
    let dop = gst::ElementFactory::make("michidop").build().unwrap();
    let filter = gst::ElementFactory::make("capsfilter").build().unwrap();
    let sink = gst::ElementFactory::make("appsink").build().unwrap();
    let appsrc = src.clone().downcast::<gstreamer_app::AppSrc>().unwrap();
    let appsink = sink.clone().downcast::<gstreamer_app::AppSink>().unwrap();
    let in_caps = gst::Caps::builder("audio/x-dsd")
        .field("format", "U8")
        .field("layout", "interleaved")
        .field("channels", 2i32)
        .field("rate", rate)
        .build();
    appsrc.set_caps(Some(&in_caps));
    appsrc.set_format(gst::Format::Time);
    in_filter.set_property("caps", &in_caps);
    dop.set_property("reverse-payload-bits", reverse);
    let out_caps = gst::Caps::builder("audio/x-raw")
        .field("format", format)
        .field("layout", "interleaved")
        .field("channels", 2i32)
        .field("rate", rate / 2)
        .build();
    filter.set_property("caps", &out_caps);
    appsink.set_sync(false);
    pipeline
        .add_many([&src, &in_filter, &dop, &filter, &sink])
        .unwrap();
    gst::Element::link_many([&src, &in_filter, &dop, &filter, &sink]).unwrap();
    pipeline.set_state(gst::State::Playing).unwrap();

    for chunk in chunks {
        let mut buffer = gst::Buffer::with_size(chunk.len()).unwrap();
        {
            let mut map = buffer.get_mut().unwrap().map_writable().unwrap();
            map.copy_from_slice(chunk);
        }
        appsrc.push_buffer(buffer).unwrap();
    }
    let mut out = Vec::new();
    for _ in 0..chunks.len() {
        let sample = appsink
            .try_pull_sample(gst::ClockTime::from_seconds(5))
            .expect("DoP output sample");
        let buffer = sample.buffer().unwrap();
        let map = buffer.map_readable().unwrap();
        out.extend_from_slice(map.as_slice());
    }
    let _ = pipeline.set_state(gst::State::Null);
    out
}

#[test]
fn packed24_golden_vector_matches_python_oracle() {
    let interleaved = [0x11, 0x55, 0x22, 0x66, 0x33, 0x77, 0x44, 0x88];
    let got = run("S24_3LE", &[&interleaved]);
    assert_eq!(
        got,
        vec![0x11, 0x22, 0x05, 0x55, 0x66, 0x05, 0x33, 0x44, 0xFA, 0x77, 0x88, 0xFA]
    );
}

#[test]
fn s32_lsb24_has_zero_padding_after_each_marker() {
    let interleaved = [0x11, 0x55, 0x22, 0x66];
    let got = run("S32LE", &[&interleaved]);
    assert_eq!(got, vec![0x11, 0x22, 0x05, 0x00, 0x55, 0x66, 0x05, 0x00]);
}

#[test]
fn marker_phase_continues_across_buffers() {
    let first = [0x11, 0x55, 0x22, 0x66];
    let second = [0x33, 0x77, 0x44, 0x88];
    let got = run("S24_3LE", &[&first, &second]);
    assert_eq!(
        got,
        vec![0x11, 0x22, 0x05, 0x55, 0x66, 0x05, 0x33, 0x44, 0xFA, 0x77, 0x88, 0xFA]
    );
}

#[test]
fn dsd128_uses_exact_carrier_rate() {
    let interleaved = [0x11, 0x55, 0x22, 0x66];
    let got = run_with("S24_3LE", &[&interleaved], 705_600, false);
    assert_eq!(got, vec![0x11, 0x22, 0x05, 0x55, 0x66, 0x05]);
}

#[test]
fn bit_reversal_is_applied_to_payload() {
    let interleaved = [0x11, 0x55, 0x22, 0x66];
    let got = run_with("S24_3LE", &[&interleaved], 352_800, true);
    assert_eq!(got, vec![0x88, 0x44, 0x05, 0xAA, 0x66, 0x05]);
}

#[test]
fn odd_chunk_retains_one_frame_until_peer_arrives() {
    let first = [0x11, 0x55, 0x22, 0x66, 0x33, 0x77];
    let second = [0x44, 0x88];
    let got = run("S24_3LE", &[&first, &second]);
    assert_eq!(
        got,
        vec![0x11, 0x22, 0x05, 0x55, 0x66, 0x05, 0x33, 0x44, 0xFA, 0x77, 0x88, 0xFA]
    );
}
