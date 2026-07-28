# This file hosts the SketchUp Ruby script that can be downloaded by the user
# to export models directly from SketchUp as structured JSON.

RUBY_EXPORTER_SCRIPT = """# SketchUp Floor Plan JSON Exporter Plugin
# Save this file as 'sketchup_json_exporter.rb' and load it in SketchUp
# or paste it into the Ruby Console (Window -> Ruby Console).

require 'json'

module SketchUpFloorPlanExporter
  def self.export_model
    model = Sketchup.active_model
    if model.nil? || model.path.empty?
      UI.messagebox("Please save the SketchUp model first.")
      return
    end

    # Ask where to save the JSON file
    default_name = File.basename(model.path, ".*") + "_exported.json"
    file_path = UI.savepanel("Export Floor Plan JSON", "", default_name)
    return if file_path.nil?

    # Prepare extraction data structure
    export_data = {
      "metadata" => {
        "name" => model.title || "Untitled Model",
        "unit" => get_unit_string(model.options["UnitsOptions"]["LengthUnit"]),
        "scale" => 1.0,
        "created_at" => Time.now.iso8601,
        "updated_at" => Time.now.iso8601
      },
      "walls" => [],
      "doors" => [],
      "windows" => [],
      "rooms" => [],
      "raw_geometry" => {
        "faces" => [],
        "edges" => [],
        "instances" => []
      }
    }

    # Extract geometry recursively with transformation stack
    identity_transform = Geom::Transformation.new
    extract_entities(model.active_entities, identity_transform, export_data)

    # Save to file
    File.open(file_path, "w") do |f|
      f.write(JSON.pretty_generate(export_data))
    end

    UI.messagebox("Model successfully exported to:\\n#{file_path}")
  end

  def self.get_unit_string(unit_int)
    # SketchUp LengthUnit options: 0=Inches, 1=Feet, 2=Millimeters, 3=Centimeters, 4=Meters
    case unit_int
    when 0 then "in"
    when 1 then "ft"
    when 2 then "mm"
    when 3 then "cm"
    when 4 then "m"
    else "mm"
    end
  end

  def self.extract_entities(entities, transform, data)
    entities.each do |entity|
      next unless entity.visible?

      layer_name = entity.layer ? entity.layer.name : "Layer0"

      if entity.is_a?(Sketchup::Face)
        # Extract vertices of the face, applying the active transformation matrix
        vertices = entity.vertices.map do |v|
          pt = v.position.transform(transform)
          { "x" => pt.x.to_m * 1000.0, "y" => pt.y.to_m * 1000.0, "z" => pt.z.to_m * 1000.0 } # Convert to millimeters
        end

        normal = entity.normal.transform(transform)

        data["raw_geometry"]["faces"] << {
          "id" => entity.persistent_id.to_s,
          "layer" => layer_name,
          "vertices" => vertices,
          "normal" => { "x" => normal.x, "y" => normal.y, "z" => normal.z },
          "material" => entity.material ? entity.material.name : nil
        }

      elsif entity.is_a?(Sketchup::Edge)
        # Save lines that don't belong to any face or general lines
        pt_start = entity.start.position.transform(transform)
        pt_end = entity.end.position.transform(transform)

        data["raw_geometry"]["edges"] << {
          "id" => entity.persistent_id.to_s,
          "layer" => layer_name,
          "start" => { "x" => pt_start.x.to_m * 1000.0, "y" => pt_start.y.to_m * 1000.0, "z" => pt_start.z.to_m * 1000.0 },
          "end" => { "x" => pt_end.x.to_m * 1000.0, "y" => pt_end.y.to_m * 1000.0, "z" => pt_end.z.to_m * 1000.0 }
        }

      elsif entity.is_a?(Sketchup::Group)
        # Recursively parse group elements
        group_transform = transform * entity.transformation
        extract_entities(entity.entities, group_transform, data)

      elsif entity.is_a?(Sketchup::ComponentInstance)
        # Recursively parse component instance elements
        comp_transform = transform * entity.transformation
        extract_entities(entity.definition.entities, comp_transform, data)
        
        # Track component instance properties (useful for Door/Window tags)
        inst_name = entity.name.downcase
        def_name = entity.definition.name.downcase
        
        # Check if labeled as structural element
        type = nil
        if inst_name.include?("door") || def_name.include?("door")
          type = "door"
        elsif inst_name.include?("window") || def_name.include?("window")
          type = "window"
        end

        if type
          bounds = entity.bounds
          center = bounds.center.transform(transform)
          data["raw_geometry"]["instances"] << {
            "id" => entity.persistent_id.to_s,
            "type" => type,
            "name" => entity.definition.name,
            "layer" => layer_name,
            "center" => { "x" => center.x.to_m * 1000.0, "y" => center.y.to_m * 1000.0, "z" => center.z.to_m * 1000.0 },
            "width" => bounds.width.to_m * 1000.0,
            "height" => bounds.height.to_m * 1000.0,
            "depth" => bounds.depth.to_m * 1000.0
          }
        end
      end
    end
  end
end

# Uncomment the following line to add menu items when loading inside SketchUp
# if not file_loaded?(__FILE__)
#   UI.menu("Plugins").add_item("Export Floor Plan JSON") { SketchUpFloorPlanExporter.export_model }
#   file_loaded(__FILE__)
# end
"""
