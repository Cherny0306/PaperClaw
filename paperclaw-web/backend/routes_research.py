"""
Research Mode API Routes

Additional API endpoints for original research mode.
"""

from flask import Blueprint, request, jsonify
from pathlib import Path

from .services import DataService, AnalysisService

# Create blueprint
research_bp = Blueprint('research', __name__, url_prefix='/api/research')

# Service instances
data_service = DataService()
analysis_service = AnalysisService()


# Data Upload Endpoints

@research_bp.route('/data/upload', methods=['POST'])
def upload_data():
    """Upload research data"""
    data = request.json

    file_content = data.get('file_content')
    filename = data.get('filename')
    data_type = data.get('data_type', 'training')
    description = data.get('description', '')

    if not file_content or not filename:
        return jsonify({"error": "Missing file content or filename"}), 400

    result = data_service.upload_data(
        file_content=file_content,
        filename=filename,
        data_type=data_type,
        description=description
    )

    if result.get("success"):
        return jsonify(result)
    else:
        return jsonify(result), 400


@research_bp.route('/data/datasets', methods=['GET'])
def list_datasets():
    """List all uploaded datasets"""
    datasets = data_service.list_datasets()
    return jsonify({"datasets": datasets})


@research_bp.route('/data/datasets/<dataset_id>', methods=['GET'])
def get_dataset(dataset_id):
    """Get dataset details"""
    dataset = data_service.get_dataset(dataset_id)

    if dataset:
        return jsonify(dataset)
    else:
        return jsonify({"error": "Dataset not found"}), 404


@research_bp.route('/data/datasets/<dataset_id>/validate', methods=['POST'])
def validate_dataset(dataset_id):
    """Validate a dataset"""
    result = data_service.validate_dataset(dataset_id)

    if result.get("success"):
        return jsonify(result)
    else:
        return jsonify(result), 400


@research_bp.route('/data/datasets/<dataset_id>/preprocess', methods=['POST'])
def preprocess_dataset(dataset_id):
    """Preprocess GeoTIFF data"""
    data = request.json
    operations = data.get('operations', ['statistics'])

    result = data_service.preprocess_geotiff(dataset_id, operations)

    if result.get("success"):
        return jsonify(result)
    else:
        return jsonify(result), 400


@research_bp.route('/data/datasets/<dataset_id>', methods=['DELETE'])
def delete_dataset(dataset_id):
    """Delete a dataset"""
    result = data_service.delete_dataset(dataset_id)

    if result.get("success"):
        return jsonify(result)
    else:
        return jsonify(result), 400


# Analysis Endpoints

@research_bp.route('/analyze/results', methods=['POST'])
def analyze_results():
    """Analyze existing model training results"""
    data = request.json

    results_file = data.get('results_file')
    model_type = data.get('model_type', 'yolo')

    if not results_file:
        return jsonify({"error": "Missing results_file"}), 400

    result = analysis_service.analyze_results(results_file, model_type)

    if result.get("success"):
        return jsonify(result)
    else:
        return jsonify(result), 400


@research_bp.route('/analyze/compare', methods=['POST'])
def compare_models():
    """Compare multiple model results"""
    data = request.json

    models = data.get('models', [])

    if not models or len(models) < 2:
        return jsonify({"error": "At least 2 models required for comparison"}), 400

    result = analysis_service.compare_models(models)

    if result.get("success"):
        return jsonify(result)
    else:
        return jsonify(result), 400


@research_bp.route('/analyze/augmentation', methods=['POST'])
def analyze_augmentation():
    """Analyze data augmentation effects"""
    data = request.json

    results_dir = data.get('results_dir')

    if not results_dir:
        return jsonify({"error": "Missing results_dir"}), 400

    result = analysis_service.analyze_augmentation(Path(results_dir))

    if result.get("success"):
        return jsonify(result)
    else:
        return jsonify(result), 400


@research_bp.route('/analyze/ablation', methods=['POST'])
def analyze_ablation():
    """Analyze ablation experiment results"""
    data = request.json

    baseline_dir = data.get('baseline_dir')
    ablated_dirs = data.get('ablated_dirs', [])

    if not baseline_dir:
        return jsonify({"error": "Missing baseline_dir"}), 400

    result = analysis_service.analyze_ablation(Path(baseline_dir), ablated_dirs)

    if result.get("success"):
        return jsonify(result)
    else:
        return jsonify(result), 400


@research_bp.route('/analyze/data', methods=['POST'])
def analyze_data():
    """Analyze tabular data"""
    data = request.json

    dataset_data = data.get('data')
    dataset_id = data.get('dataset_id')

    if dataset_id:
        # Get data from stored dataset
        dataset = data_service.get_dataset(dataset_id)
        if dataset:
            dataset_data = dataset.get('data')
        else:
            return jsonify({"error": "Dataset not found"}), 404

    if not dataset_data:
        return jsonify({"error": "No data provided"}), 400

    result = analysis_service.analyze_data(dataset_data)

    if result.get("success"):
        return jsonify(result)
    else:
        return jsonify(result), 400


@research_bp.route('/hypotheses/generate', methods=['POST'])
def generate_hypotheses():
    """Generate research hypotheses from data"""
    data = request.json

    dataset_data = data.get('data')
    dataset_id = data.get('dataset_id')
    domain = data.get('domain', 'general')

    if dataset_id:
        # Get data from stored dataset
        dataset = data_service.get_dataset(dataset_id)
        if dataset:
            dataset_data = dataset.get('data')
        else:
            return jsonify({"error": "Dataset not found"}), 404

    if not dataset_data:
        return jsonify({"error": "No data provided"}), 400

    result = analysis_service.generate_hypotheses(dataset_data, domain)

    if result.get("success"):
        return jsonify(result)
    else:
        return jsonify(result), 400


@research_bp.route('/hypotheses/prioritize', methods=['POST'])
def prioritize_hypotheses():
    """Re-prioritize hypotheses based on criteria"""
    data = request.json

    hypotheses = data.get('hypotheses', [])

    # Re-prioritize using the hypothesis generator
    from researchclaw.papercraft import HypothesisGenerator, Hypothesis, HypothesisVariable

    prioritized = []
    for h_data in hypotheses:
        h = Hypothesis(
            id=h_data.get('id', 'unknown'),
            question=h_data.get('question', ''),
            null_hypothesis=h_data.get('null_hypothesis', ''),
            alternative_hypothesis=h_data.get('alternative_hypothesis', ''),
            variables=[
                HypothesisVariable(name=v['name'], type=v['type'], data_type=v.get('data_type', 'numeric'))
                for v in h_data.get('variables', [])
            ],
            test_method=h_data.get('test_method', ''),
            novelty_score=h_data.get('novelty_score', 0),
            feasibility_score=h_data.get('feasibility_score', 0),
        )
        prioritized.append(h)

    generator = HypothesisGenerator()
    prioritized = generator.prioritize_hypotheses(prioritized)

    return jsonify({
        "success": True,
        "hypotheses": [
            {
                "id": h.id,
                "question": h.question,
                "novelty_score": h.novelty_score,
                "feasibility_score": h.feasibility_score,
                "priority": i + 1,
            }
            for i, h in enumerate(prioritized)
        ]
    })


# Paper Generation Endpoints

@research_bp.route('/paper/outline', methods=['POST'])
def generate_outline():
    """Generate paper outline"""
    data = request.json

    domain = data.get('domain', 'general')
    paper_type = data.get('paper_type', 'classification')

    # Get appropriate template outline
    from researchclaw.domains.remote_sensing.templates import RemoteSensingTemplates

    outline = RemoteSensingTemplates.get_paper_outline(paper_type)

    return jsonify({
        "success": True,
        "outline": outline,
        "domain": domain,
        "paper_type": paper_type,
    })


@research_bp.route('/paper/generate', methods=['POST'])
def generate_paper():
    """Generate full research paper"""
    data = request.json

    # Extract context
    context_dict = data.get('context', {})

    from researchclaw.papercraft.paper_writer import ResearchContext, ResearchPaperWriter

    context = ResearchContext(
        title=context_dict.get('title', 'Research Paper'),
        abstract=context_dict.get('abstract', ''),
        keywords=context_dict.get('keywords', []),
        hypotheses=context_dict.get('hypotheses', []),
        experiment_results=context_dict.get('experiment_results', {}),
        data_summary=context_dict.get('data_summary', {}),
        domain=context_dict.get('domain', 'general'),
        references=context_dict.get('references', []),
    )

    writer = ResearchPaperWriter()
    paper = writer.assemble_paper(context)
    markdown = writer.export_to_markdown(paper)

    return jsonify({
        "success": True,
        "paper": {
            "title": paper.title,
            "abstract": paper.abstract,
            "keywords": paper.keywords,
            "content": markdown,
            "metadata": paper.metadata,
        }
    })


@research_bp.route('/paper/section', methods=['POST'])
def write_section():
    """Write a specific section of the paper"""
    data = request.json

    section = data.get('section')  # introduction, methods, results, discussion, conclusion
    context_dict = data.get('context', {})

    from researchclaw.papercraft.paper_writer import ResearchContext, ResearchPaperWriter

    context = ResearchContext(
        title=context_dict.get('title', 'Research Paper'),
        abstract=context_dict.get('abstract', ''),
        keywords=context_dict.get('keywords', []),
        hypotheses=context_dict.get('hypotheses', []),
        experiment_results=context_dict.get('experiment_results', {}),
        data_summary=context_dict.get('data_summary', {}),
        domain=context_dict.get('domain', 'general'),
    )

    writer = ResearchPaperWriter()

    section_map = {
        'introduction': writer.write_introduction,
        'methods': writer.write_methods,
        'results': writer.write_results,
        'discussion': writer.write_discussion,
        'conclusion': writer.write_conclusion,
    }

    if section not in section_map:
        return jsonify({"error": f"Unknown section: {section}"}), 400

    section_content = section_map[section](context)

    return jsonify({
        "success": True,
        "section": section,
        "content": section_content.content,
    })
