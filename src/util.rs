//! simple-scan model — printing/scanning.

#[derive(Debug, Clone)]
pub struct Device {
    pub name: String,
    pub type_: String,
    pub uri: String,
    pub enabled: bool,
}

#[derive(Debug, Clone)]
pub struct Job {
    pub id: usize,
    pub device: String,
    pub status: String,
    pub pages: u32,
}

#[derive(Debug, Clone)]
pub struct Model {
    pub devices: Vec<Device>,
    pub jobs: Vec<Job>,
    next_id: usize,
}

impl Default for Model {
    fn default() -> Self { Self { devices: vec![], jobs: vec![], next_id: 1 } }
}

impl Model {
    pub fn new() -> Self { Self::default() }

    pub fn add_device(&mut self, name: &str, type_: &str, uri: &str) -> usize {
        let id = self.devices.len();
        self.devices.push(Device { name: name.into(), type_: type_.into(), uri: uri.into(), enabled: true });
        id
    }

    pub fn submit(&mut self, device: &str, pages: u32) -> Option<usize> {
        if !self.devices.iter().any(|d| d.name == device && d.enabled) { return None; }
        let id = self.next_id;
        self.next_id += 1;
        self.jobs.push(Job { id, device: device.into(), status: "pending".into(), pages });
        Some(id)
    }

    pub fn complete(&mut self, job_id: usize) -> bool {
        if let Some(j) = self.jobs.iter_mut().find(|j| j.id == job_id) {
            j.status = "completed".into();
            true
        } else { false }
    }

    pub fn cancel(&mut self, job_id: usize) -> bool {
        if let Some(j) = self.jobs.iter_mut().find(|j| j.id == job_id) {
            j.status = "canceled".into();
            true
        } else { false }
    }

    pub fn list_devices(&self) -> &[Device] { &self.devices }
    pub fn list_jobs(&self) -> &[Job] { &self.jobs }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn device_job() {
        let mut m = Model::new();
        m.add_device("laser", "printer", "ipp://localhost/printers/laser");
        let id = m.submit("laser", 3).unwrap();
        assert!(m.complete(id));
    }
}
