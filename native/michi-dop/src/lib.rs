//! Scoped M13 Gate A evaluation element: packed DSD bits -> DoP carrier.
//!
//! Input caps (evaluation contract):
//!   audio/x-dsd, format=U8, layout=interleaved, channels=2,
//!   rate={2822400,5644800,11289600}
//! Each input frame is one byte per channel (L,R). Output is interleaved
//! 24-bit DoP: two payload bytes, marker, per channel.

use std::sync::Mutex;

use gstreamer as gst;
use gstreamer::glib;
use gstreamer::prelude::*;
use gstreamer_base::subclass::prelude::*;

const PACKER_REVISION: &str = "michidop-rust-0.1.0";
const MARKER_LOW: u8 = 0x05;
const MARKER_HIGH: u8 = 0xFA;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Layout {
    Packed24,
    S32Lsb24,
}

impl Layout {
    fn bytes_per_dop_frame(self) -> usize {
        match self {
            Layout::Packed24 => 3,
            Layout::S32Lsb24 => 4,
        }
    }
}

#[derive(Debug, Default)]
struct State {
    phase_high: bool,
    pending: [u8; 4],
    pending_len: usize,
    layout: Option<Layout>,
    reverse_payload_bits: bool,
    locked: bool,
    input_rate: Option<i32>,
    output_rate: Option<i32>,
}

pub struct MichiDopImp {
    state: Mutex<State>,
}

impl Default for MichiDopImp {
    fn default() -> Self {
        Self {
            state: Mutex::new(State::default()),
        }
    }
}

#[glib::object_subclass]
impl ObjectSubclass for MichiDopImp {
    const NAME: &'static str = "MichiDop";
    type Type = MichiDop;
    type ParentType = gstreamer_base::BaseTransform;
}

impl ObjectImpl for MichiDopImp {
    fn properties() -> &'static [glib::ParamSpec] {
        static PROPERTIES: std::sync::OnceLock<Vec<glib::ParamSpec>> = std::sync::OnceLock::new();
        PROPERTIES.get_or_init(|| {
            vec![
                glib::ParamSpecBoolean::builder("reverse-payload-bits")
                    .nick("Reverse payload bits")
                    .blurb("Reverse the bit order of each input DSD byte")
                    .default_value(false)
                    .readwrite()
                    .build(),
                glib::ParamSpecString::builder("packer-revision")
                    .nick("Packer revision")
                    .blurb("Native packer revision")
                    .default_value(Some(PACKER_REVISION))
                    .read_only()
                    .build(),
            ]
        })
    }

    fn set_property(&self, _id: usize, value: &glib::Value, pspec: &glib::ParamSpec) {
        if pspec.name() == "reverse-payload-bits" {
            let enabled = value.get::<bool>().unwrap_or(false);
            if let Ok(mut state) = self.state.lock() {
                if state.locked {
                    return;
                }
                state.reverse_payload_bits = enabled;
                state.pending_len = 0;
                state.phase_high = false;
            }
        }
    }

    fn property(&self, _id: usize, pspec: &glib::ParamSpec) -> glib::Value {
        if pspec.name() == "reverse-payload-bits" {
            return self
                .state
                .lock()
                .map(|state| state.reverse_payload_bits.to_value())
                .unwrap_or_else(|_| false.to_value());
        }
        if pspec.name() == "packer-revision" {
            return PACKER_REVISION.to_value();
        }
        glib::Value::from_type(glib::Type::BOOL)
    }
}

impl ElementImpl for MichiDopImp {
    fn metadata() -> Option<&'static gst::subclass::ElementMetadata> {
        static METADATA: std::sync::OnceLock<gst::subclass::ElementMetadata> =
            std::sync::OnceLock::new();
        Some(METADATA.get_or_init(|| {
            gst::subclass::ElementMetadata::new(
                "Michi DoP packer",
                "Filter/Converter/Audio",
                "Packs DSD bits into a 24-bit DoP carrier (M13 Gate A evaluation)",
                "Michi Music Player",
            )
        }))
    }

    fn pad_templates() -> &'static [gst::PadTemplate] {
        static TEMPLATES: std::sync::OnceLock<Vec<gst::PadTemplate>> = std::sync::OnceLock::new();
        TEMPLATES.get_or_init(|| {
            let sink_caps = gst::Caps::builder("audio/x-dsd")
                .field("format", gst::List::new(["U8", "DSDU8"]))
                .field("layout", "interleaved")
                .field("channels", 2i32)
                .field("rate", gst::List::new([352_800i32, 705_600, 1_411_200]))
                .build();
            let src_caps = gst::Caps::builder("audio/x-raw")
                .field("layout", "interleaved")
                .field("channels", 2i32)
                .field("format", gst::List::new(["S24_3LE", "S32LE"]))
                .field("rate", gst::List::new([176_400i32, 352_800, 705_600]))
                .build();
            vec![
                gst::PadTemplate::new(
                    "sink",
                    gst::PadDirection::Sink,
                    gst::PadPresence::Always,
                    &sink_caps,
                )
                .unwrap(),
                gst::PadTemplate::new(
                    "src",
                    gst::PadDirection::Src,
                    gst::PadPresence::Always,
                    &src_caps,
                )
                .unwrap(),
            ]
        })
    }
}

impl BaseTransformImpl for MichiDopImp {
    const MODE: gstreamer_base::subclass::BaseTransformMode =
        gstreamer_base::subclass::BaseTransformMode::Both;
    const PASSTHROUGH_ON_SAME_CAPS: bool = false;
    const TRANSFORM_IP_ON_PASSTHROUGH: bool = false;

    fn transform_caps(
        &self,
        direction: gst::PadDirection,
        caps: &gst::Caps,
        filter: Option<&gst::Caps>,
    ) -> Option<gst::Caps> {
        if caps.is_any() {
            return Some(gst::Caps::new_any());
        }
        let Some(s) = caps.structure(0) else {
            return Some(gst::Caps::new_any());
        };
        if direction == gst::PadDirection::Sink {
            let Ok(rate) = s.get::<i32>("rate") else {
                return Some(gst::Caps::new_any());
            };
            if !matches!(rate, 352_800 | 705_600 | 1_411_200) {
                return None;
            }
            let carrier = rate / 2;
            let out = gst::Caps::builder("audio/x-raw")
                .field("layout", "interleaved")
                .field("channels", 2i32)
                .field("format", gst::List::new(["S24_3LE", "S32LE"]))
                .field("rate", carrier)
                .build();
            Some(apply_filter(out, filter))
        } else {
            let Ok(rate) = s.get::<i32>("rate") else {
                return Some(gst::Caps::new_any());
            };
            let dsd = rate.checked_mul(2)?;
            if !matches!(dsd, 352_800 | 705_600 | 1_411_200) {
                return None;
            }
            let in_caps = gst::Caps::builder("audio/x-dsd")
                .field("format", gst::List::new(["U8", "DSDU8"]))
                .field("layout", "interleaved")
                .field("channels", 2i32)
                .field("rate", dsd)
                .build();
            Some(apply_filter(in_caps, filter))
        }
    }

    fn start(&self) -> Result<(), gst::ErrorMessage> {
        let result = self.parent_start();
        if result.is_ok() {
            if let Ok(mut state) = self.state.lock() {
                state.locked = true;
            }
        }
        result
    }

    fn stop(&self) -> Result<(), gst::ErrorMessage> {
        if let Ok(mut state) = self.state.lock() {
            state.locked = false;
            state.pending_len = 0;
            state.phase_high = false;
        }
        self.parent_stop()
    }

    fn set_caps(&self, incaps: &gst::Caps, outcaps: &gst::Caps) -> Result<(), gst::LoggableError> {
        let input = incaps
            .structure(0)
            .ok_or_else(|| gst::loggable_error!(gst::CAT_RUST, "input caps missing"))?;
        let output = outcaps
            .structure(0)
            .ok_or_else(|| gst::loggable_error!(gst::CAT_RUST, "output caps missing"))?;
        let in_rate = input
            .get::<i32>("rate")
            .map_err(|_| gst::loggable_error!(gst::CAT_RUST, "input rate missing"))?;
        let out_rate = output
            .get::<i32>("rate")
            .map_err(|_| gst::loggable_error!(gst::CAT_RUST, "output rate missing"))?;
        if in_rate / 2 != out_rate {
            return Err(gst::loggable_error!(
                gst::CAT_RUST,
                "carrier rate does not match DSD-byte rate/2"
            ));
        }
        let format: &str = output
            .get::<&str>("format")
            .map_err(|_| gst::loggable_error!(gst::CAT_RUST, "output format missing"))?;
        let layout = match format {
            "S24_3LE" => Layout::Packed24,
            "S32LE" => Layout::S32Lsb24,
            other => {
                return Err(gst::loggable_error!(
                    gst::CAT_RUST,
                    "unsupported output format {other}"
                ))
            }
        };
        let mut state = self
            .state
            .lock()
            .map_err(|_| gst::loggable_error!(gst::CAT_RUST, "DoP state poisoned"))?;
        state.layout = Some(layout);
        state.input_rate = Some(in_rate);
        state.output_rate = Some(out_rate);
        state.pending_len = 0;
        state.phase_high = false;
        Ok(())
    }

    fn transform_size(
        &self,
        direction: gst::PadDirection,
        _caps: &gst::Caps,
        size: usize,
        _othercaps: &gst::Caps,
    ) -> Option<usize> {
        if direction == gst::PadDirection::Src {
            return None;
        }
        let state = self.state.lock().ok()?;
        let layout = state.layout?;
        let total = size.checked_add(state.pending_len)?;
        let frames = total / 4;
        frames.checked_mul(2 * layout.bytes_per_dop_frame())
    }

    fn transform(
        &self,
        inbuf: &gst::Buffer,
        outbuf: &mut gst::BufferRef,
    ) -> Result<gst::FlowSuccess, gst::FlowError> {
        let input = inbuf.map_readable().map_err(|_| gst::FlowError::Error)?;
        let mut output = outbuf.map_writable().map_err(|_| gst::FlowError::Error)?;
        let mut state = self.state.lock().map_err(|_| gst::FlowError::Error)?;
        let layout = state.layout.ok_or(gst::FlowError::NotNegotiated)?;
        let reverse = state.reverse_payload_bits;
        if inbuf.flags().contains(gst::BufferFlags::DISCONT) {
            state.pending_len = 0;
            state.phase_high = false;
        }
        let bytes = input.as_slice();
        let mut pending = state.pending;
        let mut pending_len = state.pending_len;
        let mut index = 0usize;
        let mut written = 0usize;
        let frame_bytes = 2 * layout.bytes_per_dop_frame();
        while pending_len == 4 || index < bytes.len() {
            while pending_len < 4 && index < bytes.len() {
                pending[pending_len] = bytes[index];
                pending_len += 1;
                index += 1;
            }
            if pending_len < 4 {
                break;
            }
            if written
                .checked_add(frame_bytes)
                .is_none_or(|end| end > output.len())
            {
                return Err(gst::FlowError::Error);
            }
            let marker = if state.phase_high {
                MARKER_HIGH
            } else {
                MARKER_LOW
            };
            state.phase_high = !state.phase_high;
            let l0 = reverse_bits(pending[0], reverse);
            let r0 = reverse_bits(pending[1], reverse);
            let l1 = reverse_bits(pending[2], reverse);
            let r1 = reverse_bits(pending[3], reverse);
            output[written] = l0;
            output[written + 1] = l1;
            output[written + 2] = marker;
            written += 3;
            if layout == Layout::S32Lsb24 {
                output[written] = 0;
                written += 1;
            }
            output[written] = r0;
            output[written + 1] = r1;
            output[written + 2] = marker;
            written += 3;
            if layout == Layout::S32Lsb24 {
                output[written] = 0;
                written += 1;
            }
            pending_len = 0;
        }
        state.pending = pending;
        state.pending_len = pending_len;
        drop(output);
        outbuf.set_size(written);
        Ok(gst::FlowSuccess::Ok)
    }

    fn sink_event(&self, event: gst::Event) -> bool {
        if event.type_() == gst::EventType::FlushStart || event.type_() == gst::EventType::FlushStop
        {
            if let Ok(mut state) = self.state.lock() {
                state.pending_len = 0;
                state.phase_high = false;
            }
        }
        if event.type_() == gst::EventType::Eos {
            if let Ok(state) = self.state.lock() {
                if state.pending_len != 0 {
                    gst::element_error!(
                        self.obj(),
                        gst::StreamError::Decode,
                        ("incomplete DoP input frame at EOS")
                    );
                    return false;
                }
            }
        }
        self.parent_sink_event(event)
    }
}

fn apply_filter(caps: gst::Caps, filter: Option<&gst::Caps>) -> gst::Caps {
    match filter {
        Some(filter) if !filter.is_any() => {
            caps.intersect_with_mode(filter, gst::CapsIntersectMode::First)
        }
        _ => caps,
    }
}

fn reverse_bits(byte: u8, enabled: bool) -> u8 {
    if enabled {
        byte.reverse_bits()
    } else {
        byte
    }
}

glib::wrapper! {
    pub struct MichiDop(ObjectSubclass<MichiDopImp>)
        @extends gstreamer_base::BaseTransform, gst::Element, gst::Object;
}

impl gstreamer::subclass::prelude::GstObjectImpl for MichiDopImp {}

fn plugin_init(plugin: &gst::Plugin) -> Result<(), glib::BoolError> {
    gst::Element::register(
        Some(plugin),
        "michidop",
        gst::Rank::NONE,
        MichiDop::static_type(),
    )
}

gst::plugin_define!(
    michidop,
    "Michi DoP carrier element (M13 Gate A evaluation)",
    plugin_init,
    "0.1.0",
    "MIT/X11",
    "michidop",
    "michidop",
    "https://github.com/pitydah/michi-music-player"
);

pub mod prelude {
    pub use gstreamer::prelude::*;
    pub use gstreamer_base::prelude::*;
}
