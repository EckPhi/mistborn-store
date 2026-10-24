use anyhow::{Context, Result, bail, ensure};
use reqwest::blocking::Client;
use serde_json::Value;
use std::{collections::BTreeSet, time::Duration};

#[derive(Clone, Debug)]
pub struct ImageRef {
    pub registry: String,
    pub repository: String,
    pub tag: String,
    pub prefix: String,
}
impl ImageRef {
    pub fn parse(image: &str) -> Result<Self> {
        ensure!(
            !image.contains(['$', '@', '\n', '\r', ' ']),
            "Use an explicit tagged image; digest/interpolated references need manual editing"
        );
        let (prefix, tag) = image
            .rsplit_once(':')
            .context("Image needs an explicit tag")?;
        ensure!(
            !tag.is_empty() && !tag.contains('/'),
            "Image needs an explicit tag"
        );
        let (registry, repository) = if let Some(repo) = prefix.strip_prefix("ghcr.io/") {
            ("ghcr.io", repo.to_string())
        } else {
            let repo = prefix.strip_prefix("docker.io/").unwrap_or(prefix);
            ensure!(
                !repo.split('/').next().unwrap_or("").contains(['.', ':']),
                "Only public Docker Hub and GHCR images are supported"
            );
            (
                "registry-1.docker.io",
                if repo.contains('/') {
                    repo.to_string()
                } else {
                    format!("library/{repo}")
                },
            )
        };
        ensure!(
            repository.split('/').all(|s| !s.is_empty()
                && s.bytes()
                    .all(|c| c.is_ascii_alphanumeric() || b"._-".contains(&c))),
            "Invalid image repository"
        );
        Ok(Self {
            registry: registry.into(),
            repository,
            tag: tag.into(),
            prefix: prefix.into(),
        })
    }
    pub fn with_tag(&self, tag: &str) -> Result<String> {
        ensure!(
            !tag.is_empty()
                && tag.len() <= 128
                && tag
                    .bytes()
                    .all(|c| c.is_ascii_alphanumeric() || b"._-".contains(&c)),
            "Invalid image tag"
        );
        ensure!(
            ![
                "latest", "stable", "nightly", "main", "master", "dev", "edge", "beta"
            ]
            .contains(&tag),
            "Choose a version or immutable build tag, not a rolling tag"
        );
        let numeric_tag = tag.strip_prefix('v').unwrap_or(tag);
        let floating_major =
            numeric_tag.len() <= 2 && numeric_tag.bytes().all(|c| c.is_ascii_digit());
        let floating_minor = numeric_tag.split('.').count() == 2
            && numeric_tag
                .split('.')
                .all(|s| !s.is_empty() && s.bytes().all(|c| c.is_ascii_digit()));
        ensure!(
            !floating_major && !floating_minor,
            "Floating major/minor tags are not reproducible"
        );
        Ok(format!("{}:{tag}", self.prefix))
    }
}
pub fn client() -> Result<Client> {
    Ok(Client::builder()
        .timeout(Duration::from_secs(30))
        .user_agent("runtipi-store-tui/0.1")
        .build()?)
}
fn token(client: &Client, image: &ImageRef) -> Result<String> {
    let url = if image.registry == "ghcr.io" {
        "https://ghcr.io/token"
    } else {
        "https://auth.docker.io/token"
    };
    let scope = format!("repository:{}:pull", image.repository);
    let service = if image.registry == "ghcr.io" {
        "ghcr.io"
    } else {
        "registry.docker.io"
    };
    let v: Value = client
        .get(url)
        .query(&[("service", service), ("scope", scope.as_str())])
        .send()?
        .error_for_status()?
        .json()?;
    Ok(v.get("token")
        .or_else(|| v.get("access_token"))
        .and_then(Value::as_str)
        .context("Registry returned no pull token")?
        .into())
}
pub fn tags(image: &str) -> Result<Vec<String>> {
    let i = ImageRef::parse(image)?;
    let c = client()?;
    let v: Value = if i.registry == "ghcr.io" {
        c.get(format!("https://ghcr.io/v2/{}/tags/list", i.repository))
            .bearer_auth(token(&c, &i)?)
            .send()?
            .error_for_status()?
            .json()?
    } else {
        c.get(format!(
            "https://hub.docker.com/v2/repositories/{}/tags",
            i.repository
        ))
        .query(&[("page_size", "100"), ("ordering", "last_updated")])
        .send()?
        .error_for_status()?
        .json()?
    };
    let list = v
        .get(if i.registry == "ghcr.io" {
            "tags"
        } else {
            "results"
        })
        .and_then(Value::as_array)
        .context("No image tags returned")?;
    let tags = list
        .iter()
        .filter_map(|v| v.as_str().or_else(|| v.get("name").and_then(Value::as_str)))
        .filter(|t| i.with_tag(t).is_ok())
        .map(String::from)
        .collect();
    Ok(tags)
}
pub fn verify(image: &str) -> Result<Vec<String>> {
    let i = ImageRef::parse(image)?;
    i.with_tag(&i.tag)?;
    let c = client()?;
    let t = token(&c, &i)?;
    let root = format!("https://{}/v2/{}", i.registry, i.repository);
    let manifest = |reference: &str| -> Result<Value> {
        Ok(c.get(format!("{root}/manifests/{reference}")).bearer_auth(&t).header("Accept","application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json, application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json").send()?.error_for_status()?.json()?)
    };
    let v = manifest(&i.tag).context("Tag is not published or repository is private")?;
    let mut arches = BTreeSet::new();
    if let Some(list) = v.get("manifests").and_then(Value::as_array) {
        for entry in list {
            if entry.pointer("/platform/os").and_then(Value::as_str) == Some("linux")
                && let Some(a) = entry
                    .pointer("/platform/architecture")
                    .and_then(Value::as_str)
                && ["amd64", "arm64"].contains(&a)
            {
                arches.insert(a.to_string());
            }
        }
    } else {
        let digest = v
            .pointer("/config/digest")
            .and_then(Value::as_str)
            .context("No image configuration")?;
        let config: Value = c
            .get(format!("{root}/blobs/{digest}"))
            .bearer_auth(&t)
            .send()?
            .error_for_status()?
            .json()?;
        if config["os"] == "linux"
            && let Some(a) = config["architecture"].as_str()
            && ["amd64", "arm64"].contains(&a)
        {
            arches.insert(a.to_string());
        }
    }
    if arches.is_empty() {
        bail!("No supported Linux AMD64/ARM64 image found");
    }
    Ok(arches.into_iter().collect())
}
pub fn icon(source: &str) -> Result<Vec<u8>> {
    use std::io::{Cursor, Read};
    let bytes = if source.starts_with("https://") {
        let mut response = client()?.get(source).send()?.error_for_status()?;
        let mut b = Vec::new();
        response
            .by_ref()
            .take(10 * 1024 * 1024 + 1)
            .read_to_end(&mut b)?;
        b
    } else {
        ensure!(
            !source.contains("://"),
            "Use an HTTPS icon URL or a local PNG/JPEG/WebP/ICO file"
        );
        let file = std::fs::File::open(source)?;
        let mut b = Vec::new();
        file.take(10 * 1024 * 1024 + 1).read_to_end(&mut b)?;
        b
    };
    ensure!(bytes.len() <= 10 * 1024 * 1024, "Icon exceeds 10 MiB");
    let mut reader = image::ImageReader::new(Cursor::new(bytes)).with_guessed_format()?;
    let mut limits = image::Limits::default();
    limits.max_image_width = Some(8192);
    limits.max_image_height = Some(8192);
    reader.limits(limits);
    let rgba = reader
        .decode()
        .context("Cannot decode icon; SVG requires conversion to PNG first")?
        .resize_exact(460, 460, image::imageops::FilterType::Lanczos3)
        .to_rgba8();
    let mut rgb = image::RgbImage::new(460, 460);
    for (x, y, p) in rgba.enumerate_pixels() {
        let a = u16::from(p[3]);
        rgb.put_pixel(
            x,
            y,
            image::Rgb(std::array::from_fn(|i| {
                ((u16::from(p[i]) * a + 255 * (255 - a)) / 255) as u8
            })),
        );
    }
    let mut result = Vec::new();
    image::codecs::jpeg::JpegEncoder::new_with_quality(&mut result, 92).encode_image(&rgb)?;
    Ok(result)
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn image_paths_and_tags() {
        assert_eq!(
            ImageRef::parse("postgres:17.5").unwrap().repository,
            "library/postgres"
        );
        let i = ImageRef::parse("ghcr.io/a/b:1.2.3").unwrap();
        assert_eq!(
            i.with_tag("0.5.0b17001").unwrap(),
            "ghcr.io/a/b:0.5.0b17001"
        );
        for tag in ["latest", "2", "2.3", "v2", "v2.3", "bad/tag", ""] {
            assert!(i.with_tag(tag).is_err());
        }
        assert!(i.with_tag("1057").is_ok());
        assert!(ImageRef::parse("localhost:5000/a:1.0.0").is_err());
    }
}

#[cfg(test)]
mod icon_tests {
    use super::*;
    #[test]
    fn transparent_png_is_resized_and_flattened_to_a_real_jpeg() {
        let temp = tempfile::tempdir().unwrap();
        let path = temp.path().join("icon.png");
        image::RgbaImage::from_pixel(8, 8, image::Rgba([10, 20, 30, 0]))
            .save(&path)
            .unwrap();
        let data = icon(path.to_str().unwrap()).unwrap();
        assert_eq!(
            image::guess_format(&data).unwrap(),
            image::ImageFormat::Jpeg
        );
        let decoded = image::load_from_memory(&data).unwrap().to_rgb8();
        assert_eq!(decoded.dimensions(), (460, 460));
        assert!(decoded.get_pixel(200, 200).0.into_iter().all(|v| v >= 250));
    }
    #[test]
    #[ignore = "Explicit public-registry smoke check; no mutations"]
    fn public_registries_return_published_tags_and_platforms() {
        for image in ["busybox:1.37.0", "ghcr.io/scryer-media/scryer:0.21.20"] {
            assert!(!tags(image).unwrap().is_empty());
            assert!(verify(image).unwrap().iter().any(|a| a == "amd64"));
        }
    }
}
