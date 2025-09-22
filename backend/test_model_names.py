import timm

# Find all models with 'inat' in the name
inat_models = timm.list_models('*inat*')
print("iNaturalist models available:", inat_models)

# Find all Vision Transformer models
vit_models = timm.list_models('vit*')
print("ViT models:", vit_models)