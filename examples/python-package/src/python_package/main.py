import native_component  # pants: no-infer-dep

print("Finished importing Rust module", flush=True)

native_component.main()
print("Finished running Rust module", flush=True)
