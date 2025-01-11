"""OpenStudio material translators."""
from honeybee_energy.material.opaque import EnergyMaterial, EnergyMaterialNoMass, \
    EnergyMaterialVegetation
from honeybee_energy.material.glazing import EnergyWindowMaterialGlazing, \
    EnergyWindowMaterialSimpleGlazSys
from honeybee_energy.material.gas import EnergyWindowMaterialGas, \
    EnergyWindowMaterialGasMixture, EnergyWindowMaterialGasCustom
from honeybee_energy.material.frame import EnergyWindowFrame
from honeybee_energy.material.shade import EnergyWindowMaterialShade, \
    EnergyWindowMaterialBlind

from honeybee_openstudio.openstudio import OSStandardOpaqueMaterial, \
    OSMasslessOpaqueMaterial, OSRoofVegetation, OSStandardGlazing, OSSimpleGlazing, \
    OSGas, OSGasMixture, OSShade, OSBlind, OSWindowPropertyFrameAndDivider


def opaque_material_to_openstudio(material, model):
    """Convert Honeybee EnergyMaterial to OpenStudio StandardOpaqueMaterial."""
    os_opaque_mat = OSStandardOpaqueMaterial(model)
    os_opaque_mat.setName(material.identifier)
    if material._display_name is not None:
        os_opaque_mat.setDisplayName(material.display_name)
    os_opaque_mat.setThickness(material.thickness)
    os_opaque_mat.setConductivity(material.conductivity)
    os_opaque_mat.setDensity(material.density)
    os_opaque_mat.setSpecificHeat(material.specific_heat)
    os_opaque_mat.setRoughness(material.roughness)
    os_opaque_mat.setThermalAbsorptance(material.thermal_absorptance)
    os_opaque_mat.setSolarAbsorptance(material.solar_absorptance)
    os_opaque_mat.setVisibleAbsorptance(material.visible_absorptance)
    return os_opaque_mat


def opaque_no_mass_material_to_openstudio(material, model):
    """Convert Honeybee EnergyMaterialNoMass to OpenStudio MasslessOpaqueMaterial."""
    os_nomass_mat = OSMasslessOpaqueMaterial(model)
    os_nomass_mat.setName(material.identifier)
    if material._display_name is not None:
        os_nomass_mat.setDisplayName(material.display_name)
    os_nomass_mat.setThermalResistance(material.r_value)
    os_nomass_mat.setRoughness(material.roughness)
    os_nomass_mat.setThermalAbsorptance(material.thermal_absorptance)
    os_nomass_mat.setSolarAbsorptance(material.solar_absorptance)
    os_nomass_mat.setVisibleAbsorptance(material.visible_absorptance)
    return os_nomass_mat


def vegetation_material_to_openstudio(material, model):
    """Convert Honeybee EnergyMaterialVegetation to OpenStudio RoofVegetation."""
    os_veg_mat = OSRoofVegetation(model)
    os_veg_mat.setName(material.identifier)
    if material._display_name is not None:
        os_veg_mat.setDisplayName(material.display_name)
    os_veg_mat.setThickness(material.thickness)
    os_veg_mat.setConductivityofDrySoil(material.conductivity)
    os_veg_mat.setDensityofDrySoil(material.density)
    os_veg_mat.setSpecificHeatofDrySoil(material.specific_heat)
    os_veg_mat.setRoughness(material.roughness)
    os_veg_mat.setThermalAbsorptance(material.soil_thermal_absorptance)
    os_veg_mat.setSolarAbsorptance(material.soil_solar_absorptance)
    os_veg_mat.setVisibleAbsorptance(material.soil_visible_absorptance)
    os_veg_mat.setHeightofPlants(material.plant_height)
    os_veg_mat.setLeafAreaIndex(material.leaf_area_index)
    os_veg_mat.setLeafReflectivity(material.leaf_reflectivity)
    os_veg_mat.setLeafEmissivity(material.leaf_emissivity)
    os_veg_mat.setMinimumStomatalResistance(material.min_stomatal_resist)
    os_veg_mat.setSaturationVolumetricMoistureContentoftheSoilLayer(material.sat_vol_moist_cont)
    os_veg_mat.setResidualVolumetricMoistureContentoftheSoilLayer(material.residual_vol_moist_cont)
    os_veg_mat.setInitialVolumetricMoistureContentoftheSoilLayer(material.init_vol_moist_cont)
    os_veg_mat.setMoistureDiffusionCalculationMethod(material.moist_diff_model)
    return os_veg_mat


def glazing_material_to_openstudio(material, model):
    """Convert Honeybee EnergyWindowMaterialGlazing to OpenStudio StandardGlazing."""
    os_glazing = OSStandardGlazing(model)
    os_glazing.setName(material.identifier)
    if material._display_name is not None:
        os_glazing.setDisplayName(material.display_name)
    os_glazing.setThickness(material.thickness)
    os_glazing.setSolarTransmittanceatNormalIncidence(material.solar_transmittance)
    os_glazing.setFrontSideSolarReflectanceatNormalIncidence(material.solar_reflectance)
    os_glazing.setBackSideSolarReflectanceatNormalIncidence(material.solar_reflectance_back)
    os_glazing.setVisibleTransmittanceatNormalIncidence(material.visible_transmittance)
    os_glazing.setFrontSideVisibleReflectanceatNormalIncidence(material.visible_reflectance)
    os_glazing.setBackSideVisibleReflectanceatNormalIncidence(material.visible_reflectance_back)
    os_glazing.setInfraredTransmittanceatNormalIncidence(material.infrared_transmittance)
    os_glazing.setFrontSideInfraredHemisphericalEmissivity(material.emissivity)
    os_glazing.setBackSideInfraredHemisphericalEmissivity(material.emissivity_back)
    os_glazing.setThermalConductivity(material.conductivity)
    os_glazing.setDirtCorrectionFactorforSolarandVisibleTransmittance(material.dirt_correction)
    os_glazing.setSolarDiffusing(material.solar_diffusing)
    return os_glazing


def simple_glazing_sys_material_to_openstudio(material, model):
    """Convert Honeybee EnergyWindowMaterialSimpleGlazSys to OpenStudio SimpleGlazing."""
    os_glz_sys = OSSimpleGlazing(model)
    os_glz_sys.setName(material.identifier)
    if material._display_name is not None:
        os_glz_sys.setDisplayName(material.display_name)
    os_glz_sys.setUFactor(material.u_factor)
    os_glz_sys.setSolarHeatGainCoefficient(material.shgc)
    os_glz_sys.setVisibleTransmittance(material.vt)
    return os_glz_sys


def gas_material_to_openstudio(material, model):
    """Convert Honeybee EnergyWindowMaterialGas to OpenStudio Gas."""
    os_gas = OSGas(model)
    os_gas.setName(material.identifier)
    if material._display_name is not None:
        os_gas.setDisplayName(material.display_name)
    os_gas.setThickness(material.thickness)
    os_gas.setGasType(material.gas_type)
    return os_gas


def gas_mixture_material_to_openstudio(material, model):
    """Convert Honeybee EnergyWindowMaterialGasMixture to OpenStudio GasMixture."""
    os_gas_mix = OSGasMixture(model)
    os_gas_mix.setName(material.identifier)
    if material._display_name is not None:
        os_gas_mix.setDisplayName(material.display_name)
    os_gas_mix.setThickness(material.thickness)
    for i in range(len(material.gas_types)):
        os_gas_mix.setGasType(i, material.gas_types[i])
        os_gas_mix.setGasFraction(i, material.gas_fractions[i])
    return os_gas_mix


def gas_custom_material_to_openstudio(material, model):
    """Convert Honeybee EnergyWindowMaterialGasCustom to OpenStudio Gas."""
    os_gas_custom = OSGas(model)
    os_gas_custom.setName(material.identifier)
    if material._display_name is not None:
        os_gas_custom.setDisplayName(material.display_name)
    os_gas_custom.setThickness(material.thickness)
    os_gas_custom.setGasType('Custom')
    os_gas_custom.setConductivityCoefficientA(material.conductivity_coeff_a)
    os_gas_custom.setViscosityCoefficientA(material.viscosity_coeff_a)
    os_gas_custom.setSpecificHeatCoefficientA(material.specific_heat_coeff_a)
    os_gas_custom.setConductivityCoefficientB(material.conductivity_coeff_b)
    os_gas_custom.setViscosityCoefficientB(material.viscosity_coeff_b)
    os_gas_custom.setSpecificHeatCoefficientB(material.specific_heat_coeff_b)
    os_gas_custom.setConductivityCoefficientC(material.conductivity_coeff_c)
    os_gas_custom.setViscosityCoefficientC(material.viscosity_coeff_c)
    os_gas_custom.setSpecificHeatCoefficientC(material.specific_heat_coeff_c)
    os_gas_custom.setSpecificHeatRatio(material.specific_heat_ratio)
    os_gas_custom.setMolecularWeight(material.molecular_weight)
    return os_gas_custom


def shade_material_to_openstudio(material, model):
    """Convert Honeybee EnergyWindowMaterialShade to OpenStudio Shade."""
    os_shade_mat = OSShade(model)
    os_shade_mat.setName(material.identifier)
    if material._display_name is not None:
        os_shade_mat.setDisplayName(material.display_name)
    os_shade_mat.setSolarTransmittance(material.solar_transmittance)
    os_shade_mat.setSolarReflectance(material.solar_reflectance)
    os_shade_mat.setVisibleTransmittance(material.visible_transmittance)
    os_shade_mat.setVisibleReflectance(material.visible_reflectance)
    os_shade_mat.setThermalHemisphericalEmissivity(material.emissivity)
    os_shade_mat.setThermalTransmittance(material.infrared_transmittance)
    os_shade_mat.setThickness(material.thickness)
    os_shade_mat.setConductivity(material.conductivity)
    os_shade_mat.setShadetoGlassDistance(material.distance_to_glass)
    os_shade_mat.setTopOpeningMultiplier(material.top_opening_multiplier)
    os_shade_mat.setBottomOpeningMultiplier(material.bottom_opening_multiplier)
    os_shade_mat.setLeftSideOpeningMultiplier(material.left_opening_multiplier)
    os_shade_mat.setRightSideOpeningMultiplier(material.right_opening_multiplier)
    os_shade_mat.setAirflowPermeability(material.airflow_permeability)
    return os_shade_mat


def blind_material_to_openstudio(material, model):
    """Convert Honeybee EnergyWindowMaterialBlind to OpenStudio Blind."""
    os_blind = OSBlind(model)
    os_blind.setName(material.identifier)
    if material._display_name is not None:
        os_blind.setDisplayName(material.display_name)
    os_blind.setSlatOrientation(material.slat_orientation)
    os_blind.setSlatWidth(material.slat_width)
    os_blind.setSlatSeparation(material.slat_separation)
    os_blind.setSlatThickness(material.slat_thickness)
    os_blind.setSlatAngle(material.slat_angle)
    os_blind.setSlatConductivity(material.slat_conductivity)
    os_blind.setSlatBeamSolarTransmittance(material.beam_solar_transmittance)
    os_blind.setFrontSideSlatBeamSolarReflectance(material.beam_solar_reflectance)
    os_blind.setBackSideSlatBeamSolarReflectance(material.beam_solar_reflectance_back)
    os_blind.setSlatDiffuseSolarTransmittance(material.diffuse_solar_transmittance)
    os_blind.setFrontSideSlatDiffuseSolarReflectance(material.diffuse_solar_reflectance)
    os_blind.setBackSideSlatDiffuseSolarReflectance(material.diffuse_solar_reflectance_back)
    os_blind.setSlatDiffuseVisibleTransmittance(material.diffuse_visible_transmittance)
    os_blind.setFrontSideSlatDiffuseVisibleReflectance(material.diffuse_visible_reflectance)
    os_blind.setBackSideSlatDiffuseVisibleReflectance(material.diffuse_visible_reflectance_back)
    os_blind.setSlatBeamVisibleTransmittance(material.beam_visible_transmittance)
    os_blind.setFrontSideSlatBeamVisibleReflectance(material.beam_visible_reflectance)
    os_blind.setBackSideSlatBeamVisibleReflectance(material.beam_visible_reflectance_back)
    os_blind.setSlatInfraredHemisphericalTransmittance(material.infrared_transmittance)
    os_blind.setFrontSideSlatInfraredHemisphericalEmissivity(material.emissivity)
    os_blind.setBackSideSlatInfraredHemisphericalEmissivity(material.emissivity_back)
    os_blind.setBlindtoGlassDistance(material.distance_to_glass)
    os_blind.setBlindTopOpeningMultiplier(material.top_opening_multiplier)
    os_blind.setBlindBottomOpeningMultiplier(material.bottom_opening_multiplier)
    os_blind.setBlindLeftSideOpeningMultiplier(material.left_opening_multiplier)
    os_blind.setBlindRightSideOpeningMultiplier(material.right_opening_multiplier)
    return os_blind


def frame_material_to_openstudio(material, model):
    """Convert Honeybee EnergyWindowFrame to OpenStudio WindowPropertyFrameAndDivider."""
    os_frame_mat = OSWindowPropertyFrameAndDivider(model)
    os_frame_mat.setName(material.identifier)
    if material._display_name is not None:
        os_frame_mat.setDisplayName(material.display_name)
    os_frame_mat.setFrameWidth(material.width)
    os_frame_mat.setFrameConductance(material.conductance)
    os_frame_mat.setRatioOfFrameEdgeGlassConductanceToCenterOfGlassConductance(
        material.edge_to_center_ratio)
    os_frame_mat.setFrameOutsideProjection(material.outside_projection)
    os_frame_mat.setFrameInsideProjection(material.inside_projection)
    os_frame_mat.setFrameThermalHemisphericalEmissivity(material.thermal_absorptance)
    os_frame_mat.setFrameSolarAbsorptance(material.solar_absorptance)
    os_frame_mat.setFrameVisibleAbsorptance(material.visible_absorptance)
    return os_frame_mat


def material_to_openstudio(material, model):
    """Convert any Honeybee energy material into an OpenStudio object.

    Args:
        material: A honeybee-energy Python object of a material layer.
        model: The OpenStudio Model object to which the Room will be added.

    Returns:
        An OpenStudio object for the material.
    """
    if isinstance(material, EnergyMaterial):
        return opaque_material_to_openstudio(material, model)
    elif isinstance(material, EnergyMaterialNoMass):
        return opaque_no_mass_material_to_openstudio(material, model)
    elif isinstance(material, EnergyMaterialVegetation):
        return vegetation_material_to_openstudio(material, model)
    elif isinstance(material, EnergyWindowMaterialGlazing):
        return glazing_material_to_openstudio(material, model)
    elif isinstance(material, EnergyWindowMaterialSimpleGlazSys):
        return simple_glazing_sys_material_to_openstudio(material, model)
    elif isinstance(material, EnergyWindowMaterialGas):
        return gas_material_to_openstudio(material, model)
    elif isinstance(material, EnergyWindowMaterialGasMixture):
        return gas_mixture_material_to_openstudio(material, model)
    elif isinstance(material, EnergyWindowMaterialGasCustom):
        return gas_custom_material_to_openstudio(material, model)
    elif isinstance(material, EnergyWindowFrame):
        return frame_material_to_openstudio(material, model)
    elif isinstance(material, EnergyWindowMaterialShade):
        return shade_material_to_openstudio(material, model)
    elif isinstance(material, EnergyWindowMaterialBlind):
        return blind_material_to_openstudio(material, model)
    else:
        raise ValueError(
            '{} is not a recognized Energy Material type'.format(type(material)))
