use pyo3::prelude::*;

#[pyfunction]
fn main() {
    println!("Hello, world!")
}

#[pymodule]
fn native_component(py: Python<'_>, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(main, m)?)?;
    Ok(())
}
