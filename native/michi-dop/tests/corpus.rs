//! Shared Python/Rust corpus parity for the scoped Gate A element.

use std::path::PathBuf;

use gstreamer as gst;
use gstreamer::prelude::*;

#[derive(serde::Deserialize)]
struct Vector {
    id: String,
    source: Source,
    layout: String,
    reverse_bits: bool,
    expected_hex: String,
    #[serde(default = "default_carrier_rate")]
    carrier_rate_hz: i32,
    #[serde(default)]
    chunks: Option<Vec<String>>,
}

#[derive(serde::Deserialize)]
struct Source {
    left_hex: String,
    right_hex: String,
}

fn default_carrier_rate() -> i32 {
    176_400
}

fn vectors_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .join("tests/dop/conformance/vectors")
}

fn interleave(chunk: usize, left: &[u8], right: &[u8], offset: usize) -> Vec<u8> {
    let mut out = Vec::with_capacity(chunk * 2);
    for index in offset..offset + chunk {
        out.push(left[index]);
        out.push(right[index]);
    }
    out
}

fn run(vector: &Vector) -> Vec<u8> {
    gst::init().unwrap();
    if std::env::var_os("MICHI_DOP_INSTALLED").is_none() {
        michidop::plugin_register_static().unwrap();
    }
    let left = hex::decode(&vector.source.left_hex).unwrap();
    let right = hex::decode(&vector.source.right_hex).unwrap();
    let chunks: Vec<usize> = vector
        .chunks
        .as_ref()
        .map(|items| items.iter().map(|item| item.parse().unwrap()).collect())
        .unwrap_or_else(|| vec![left.len()]);
    let mut offset = 0usize;
    let mut payloads: Vec<Vec<u8>> = Vec::new();
    for chunk in chunks {
        payloads.push(interleave(chunk, &left, &right, offset));
        offset += chunk;
    }
    assert_eq!(offset, left.len());
    run_element(
        &vector.layout,
        &payloads,
        vector.carrier_rate_hz * 2,
        vector.reverse_bits,
    )
}

fn run_element(layout: &str, chunks: &[Vec<u8>], rate: i32, reverse: bool) -> Vec<u8> {
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
    let format = match layout {
        "packed_24_le" => "S24_3LE",
        "s32_le_lsb24" | "s32_lsb24" => "S32LE",
        other => panic!("unsupported corpus layout {other}"),
    };
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
    for _ in chunks {
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
fn plugin_matches_every_applicable_python_vector() {
    let mut checked = 0usize;
    for entry in std::fs::read_dir(vectors_dir()).unwrap() {
        let path = entry.unwrap().path();
        if path.extension().and_then(|value| value.to_str()) != Some("json") {
            continue;
        }
        let Ok(vector) = serde_json::from_str::<Vector>(&std::fs::read_to_string(&path).unwrap())
        else {
            continue;
        };
        if !matches!(
            vector.layout.as_str(),
            "packed_24_le" | "s32_le_lsb24" | "s32_lsb24"
        ) {
            continue;
        }
        let got = run(&vector);
        let expected = hex::decode(&vector.expected_hex).unwrap();
        assert_eq!(got, expected, "vector {}", vector.id);
        checked += 1;
    }
    if checked < 5 {
        let dir = vectors_dir();
        eprintln!("vectors dir: {dir:?}");
        for entry in std::fs::read_dir(&dir).unwrap() {
            let path = entry.unwrap().path();
            eprintln!("vector: {path:?}");
        }
    }
    assert!(checked >= 5, "expected at least five applicable vectors");
}
